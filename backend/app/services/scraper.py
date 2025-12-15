"""Web scraping service with SSRF protection, limits, and detailed debugging"""
import asyncio
import hashlib
import ipaddress
import time
from typing import List, Set, Optional, Tuple, Dict, Any
from urllib.parse import urlparse, urljoin, urlunparse
from datetime import datetime
import httpx
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from app.config import get_settings
from app.models import AuditJob, ScrapedPage

settings = get_settings()

# Realistic browser headers to avoid basic bot detection
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


class ScrapeDebug:
    """Collect debug information during scraping"""
    
    def __init__(self, input_url: str):
        self.input_url = input_url
        self.normalized_url = None
        self.final_url = None
        self.homepage_status_code = None
        self.homepage_fetch_error = None
        self.robots_txt_status = None
        self.robots_disallows_all = False
        self.sitemap_found = False
        self.sitemap_urls_count = 0
        self.links_extracted_from_homepage = 0
        self.blocked_reason = None  # 403_waf | timeout | dns | ssl | parse_error | redirect_loop | unknown
        self.pages_attempted = 0
        self.pages_success = 0
        self.pages_failed = 0
        self.timings = {
            "home_fetch_ms": 0,
            "sitemap_ms": 0,
            "total_ms": 0
        }
        self.errors = []  # List of error strings
        self.start_time = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        self.timings["total_ms"] = int((time.time() - self.start_time) * 1000)
        return {
            "input_url": self.input_url,
            "normalized_url": self.normalized_url,
            "final_url": self.final_url,
            "homepage_status_code": self.homepage_status_code,
            "homepage_fetch_error": self.homepage_fetch_error,
            "robots_txt_status": self.robots_txt_status,
            "robots_disallows_all": self.robots_disallows_all,
            "sitemap_found": self.sitemap_found,
            "sitemap_urls_count": self.sitemap_urls_count,
            "links_extracted_from_homepage": self.links_extracted_from_homepage,
            "blocked_reason": self.blocked_reason,
            "pages_attempted": self.pages_attempted,
            "pages_success": self.pages_success,
            "pages_failed": self.pages_failed,
            "timings": self.timings,
            "errors": self.errors[:20]  # Limit to 20 errors
        }


class SSRFProtection:
    """SSRF protection validator"""
    
    PRIVATE_IP_RANGES = [
        ipaddress.ip_network("10.0.0.0/8"),
        ipaddress.ip_network("172.16.0.0/12"),
        ipaddress.ip_network("192.168.0.0/16"),
        ipaddress.ip_network("127.0.0.0/8"),
        ipaddress.ip_network("169.254.0.0/16"),
        ipaddress.ip_network("::1/128"),
        ipaddress.ip_network("fc00::/7"),
        ipaddress.ip_network("fe80::/10"),
    ]
    
    @classmethod
    def is_safe_url(cls, url: str) -> bool:
        """Check if URL is safe (not SSRF)"""
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ["http", "https"]:
                return False
            if parsed.hostname in ["localhost", "127.0.0.1", "::1"]:
                return False
            try:
                ip = ipaddress.ip_address(parsed.hostname)
                for private_range in cls.PRIVATE_IP_RANGES:
                    if ip in private_range:
                        return False
            except ValueError:
                pass
            return True
        except Exception:
            return False


class WebScraper:
    """Web scraper with detailed debugging and diagnostics"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=10.0,
                read=settings.request_timeout,
                write=10.0,
                pool=10.0
            ),
            follow_redirects=True,
            max_redirects=5,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            headers=DEFAULT_HEADERS,
        )
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
    
    def normalize_url(self, url: str) -> str:
        """Normalize URL for deduplication and consistency"""
        parsed = urlparse(url)
        
        # Normalize scheme to https
        scheme = "https" if parsed.scheme == "http" else parsed.scheme
        
        # Normalize hostname (lowercase, remove www if present for comparison)
        hostname = parsed.netloc.lower()
        
        # Normalize path
        path = parsed.path.rstrip("/") or "/"
        
        normalized = urlunparse((
            scheme,
            hostname,
            path,
            parsed.params,
            parsed.query,
            ""  # No fragment
        ))
        
        return normalized
    
    def get_url_hash(self, url: str) -> str:
        """Get SHA256 hash of normalized URL"""
        normalized = self.normalize_url(url)
        return hashlib.sha256(normalized.encode()).hexdigest()
    
    def identify_page_priority(self, url: str) -> int:
        """Identify page priority for sampling"""
        url_lower = url.lower()
        
        # Homepage
        path = urlparse(url_lower).path.rstrip('/')
        if path == '' or path == '/':
            return 0
        
        # High priority
        high_priority = ['about', 'pricing', 'price', 'services', 'products', 'solutions',
                        'case-stud', 'portfolio', 'customers', 'testimonial', 'reviews']
        for keyword in high_priority:
            if keyword in url_lower:
                return 1
        
        # Medium priority
        medium_priority = ['faq', 'contact', 'blog', 'features', 'resources', 'how-it-works',
                          'use-case', 'industries', 'team']
        for keyword in medium_priority:
            if keyword in url_lower:
                return 2
        
        return 3
    
    async def check_robots(self, domain: str, debug: ScrapeDebug) -> bool:
        """Check robots.txt - returns True if crawling is allowed"""
        robots_url = f"https://{domain}/robots.txt"
        start = time.time()
        
        try:
            response = await self.client.get(robots_url, timeout=5.0)
            debug.robots_txt_status = response.status_code
            
            if response.status_code == 200:
                content = response.text.lower()
                # Very basic check - look for blanket disallow
                if "disallow: /" in content and "user-agent: *" in content:
                    # Check if it's truly blanket
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if 'user-agent: *' in line:
                            for j in range(i+1, min(i+5, len(lines))):
                                if 'disallow: /' in lines[j] and lines[j].strip() == 'disallow: /':
                                    debug.robots_disallows_all = True
                                    return False
            return True
        except Exception as e:
            debug.robots_txt_status = "error"
            debug.errors.append(f"robots.txt: {str(e)[:100]}")
            return True  # Allow if we can't check
    
    async def fetch_page(self, url: str, debug: ScrapeDebug, is_homepage: bool = False) -> Optional[Tuple[str, str, str, str, int]]:
        """
        Fetch a single page with detailed error tracking
        Returns: (html_content, text_content, title, meta_description, status_code) or None
        """
        if not SSRFProtection.is_safe_url(url):
            debug.errors.append(f"SSRF blocked: {url[:50]}")
            return None
        
        debug.pages_attempted += 1
        start_time = time.time()
        
        try:
            # Longer timeout for homepage
            timeout = 15.0 if is_homepage else settings.request_timeout
            response = await self.client.get(url, timeout=timeout)
            
            fetch_time = int((time.time() - start_time) * 1000)
            
            if is_homepage:
                debug.timings["home_fetch_ms"] = fetch_time
                debug.homepage_status_code = response.status_code
                debug.final_url = str(response.url)
            
            # Check for blocking status codes
            if response.status_code in [403, 406, 429, 503]:
                if is_homepage:
                    debug.blocked_reason = "403_waf"
                    debug.homepage_fetch_error = f"HTTP {response.status_code}"
                debug.pages_failed += 1
                return None
            
            if response.status_code >= 400:
                debug.pages_failed += 1
                return None
            
            # Check content type
            content_type = response.headers.get("content-type", "")
            if "text/html" not in content_type.lower():
                return None
            
            # Check size
            content_length = len(response.content)
            if content_length > settings.max_page_size_mb * 1024 * 1024:
                debug.errors.append(f"Page too large: {url[:50]} ({content_length} bytes)")
                return None
            
            html_content = response.text
            soup = BeautifulSoup(html_content, "lxml")
            
            # Extract text
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            text_content = soup.get_text(separator=" ", strip=True)
            
            # Extract title
            title = soup.title.string if soup.title else ""
            
            # Extract meta description
            meta_desc = ""
            meta_tag = soup.find("meta", attrs={"name": "description"})
            if meta_tag and meta_tag.get("content"):
                meta_desc = meta_tag["content"]
            
            debug.pages_success += 1
            return (html_content, text_content, title or "", meta_desc, response.status_code)
            
        except httpx.TimeoutException as e:
            if is_homepage:
                debug.blocked_reason = "timeout"
                debug.homepage_fetch_error = f"Timeout: {str(e)[:50]}"
            debug.pages_failed += 1
            debug.errors.append(f"Timeout: {url[:50]}")
            return None
        except httpx.ConnectError as e:
            error_str = str(e).lower()
            if is_homepage:
                if "ssl" in error_str or "certificate" in error_str:
                    debug.blocked_reason = "ssl"
                elif "dns" in error_str or "name" in error_str:
                    debug.blocked_reason = "dns"
                else:
                    debug.blocked_reason = "connection"
                debug.homepage_fetch_error = str(e)[:100]
            debug.pages_failed += 1
            debug.errors.append(f"Connect error: {str(e)[:50]}")
            return None
        except Exception as e:
            if is_homepage:
                debug.blocked_reason = "unknown"
                debug.homepage_fetch_error = str(e)[:100]
            debug.pages_failed += 1
            debug.errors.append(f"Error: {str(e)[:50]}")
            return None
    
    async def extract_links(self, html: str, base_url: str, debug: ScrapeDebug) -> Set[str]:
        """Extract all links from HTML"""
        soup = BeautifulSoup(html, "lxml")
        links = set()
        base_domain = urlparse(base_url).netloc.lower()
        
        for a in soup.find_all("a", href=True):
            href = a["href"]
            absolute_url = urljoin(base_url, href)
            parsed = urlparse(absolute_url)
            
            # Only keep same domain, http(s), and reasonable paths
            if parsed.netloc.lower() == base_domain and parsed.scheme in ['http', 'https']:
                # Skip obvious non-content URLs
                skip_patterns = ['.pdf', '.jpg', '.png', '.gif', '.zip', '.exe', 
                               'javascript:', 'mailto:', 'tel:', '#']
                if not any(pattern in absolute_url.lower() for pattern in skip_patterns):
                    links.add(self.normalize_url(absolute_url))
        
        return links
    
    async def find_sitemap(self, domain: str, debug: ScrapeDebug) -> Optional[List[str]]:
        """Try to find and parse sitemap.xml"""
        sitemap_urls_to_try = [
            f"https://{domain}/sitemap.xml",
            f"https://{domain}/sitemap_index.xml",
            f"https://www.{domain}/sitemap.xml",
        ]
        
        start = time.time()
        
        for sitemap_url in sitemap_urls_to_try:
            try:
                response = await self.client.get(sitemap_url, timeout=5.0)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, "xml")
                    urls = [loc.text for loc in soup.find_all("loc")]
                    if urls:
                        debug.sitemap_found = True
                        debug.sitemap_urls_count = len(urls)
                        debug.timings["sitemap_ms"] = int((time.time() - start) * 1000)
                        return urls[:100]
            except Exception as e:
                debug.errors.append(f"Sitemap {sitemap_url[:30]}: {str(e)[:30]}")
                continue
        
        debug.timings["sitemap_ms"] = int((time.time() - start) * 1000)
        return None
    
    async def scrape_domain(
        self,
        domain: str,
        job_id: str,
        is_target: bool = True,
        max_pages: int = 60,
    ) -> Tuple[int, List[str], ScrapeDebug]:
        """
        Scrape a domain with detailed debugging
        Returns: (pages_scraped, priority_urls, debug_info)
        """
        # Initialize debug
        debug = ScrapeDebug(domain)
        
        # Normalize domain and build start URL
        domain = domain.replace("https://", "").replace("http://", "").strip("/")
        start_url = f"https://{domain}"
        debug.normalized_url = start_url
        
        visited = set()
        to_visit = set()
        pages_scraped = 0
        priority_urls = []
        
        # Check robots.txt first
        await self.check_robots(domain, debug)
        if debug.robots_disallows_all:
            debug.blocked_reason = "robots_disallow"
            debug.errors.append("robots.txt disallows all crawling")
            return 0, [], debug
        
        # Fetch homepage first (critical)
        print(f"[SCRAPE] Fetching homepage: {start_url}")
        homepage_result = await self.fetch_page(start_url, debug, is_homepage=True)
        
        if not homepage_result:
            # Homepage failed - this is a critical failure
            if not debug.blocked_reason:
                debug.blocked_reason = "homepage_failed"
            print(f"[SCRAPE] Homepage failed: {debug.blocked_reason}")
            return 0, [], debug
        
        html_content, text_content, title, meta_desc, status_code = homepage_result
        
        # Save homepage
        url_hash = self.get_url_hash(start_url)
        # Guard against duplicates (within job and/or global uniqueness depending on DB schema)
        existing_home = await self.db.execute(
            select(ScrapedPage).where(
                ScrapedPage.url_hash == url_hash,
                ScrapedPage.audit_job_id == job_id,
            )
        )
        if not existing_home.scalar_one_or_none():
            page = ScrapedPage(
                audit_job_id=job_id,
                url=debug.final_url or start_url,
                domain=domain,
                is_target=is_target,
                html_content=html_content,
                text_content=text_content,
                title=title,
                meta_description=meta_desc,
                status_code=status_code,
                content_type="text/html",
                word_count=len(text_content.split()),
                url_hash=url_hash,
            )
            self.db.add(page)
            try:
                await self.db.commit()
            except IntegrityError:
                # If DB schema enforces global uniqueness or another race inserted it, skip gracefully
                await self.db.rollback()
        
        visited.add(start_url)
        priority_urls.append(debug.final_url or start_url)
        pages_scraped = 1
        
        # Extract links from homepage
        homepage_links = await self.extract_links(html_content, start_url, debug)
        debug.links_extracted_from_homepage = len(homepage_links)
        
        # Sort by priority
        sorted_links = sorted(homepage_links, key=lambda x: self.identify_page_priority(x))
        for link in sorted_links:
            if link not in visited:
                to_visit.add(link)
        
        # Try sitemap
        sitemap_urls = await self.find_sitemap(domain, debug)
        if sitemap_urls:
            for url in sitemap_urls:
                normalized = self.normalize_url(url)
                if normalized not in visited:
                    to_visit.add(normalized)
        
        # Crawl remaining pages
        while to_visit and pages_scraped < max_pages:
            url = to_visit.pop()
            
            if url in visited:
                continue
            
            # Check for existing (within this job only - same URL allowed in different jobs)
            url_hash = self.get_url_hash(url)
            existing = await self.db.execute(
                select(ScrapedPage).where(
                    ScrapedPage.url_hash == url_hash,
                    ScrapedPage.audit_job_id == job_id
                )
            )
            if existing.scalar_one_or_none():
                visited.add(url)
                continue
            
            # Fetch page
            result = await self.fetch_page(url, debug)
            if not result:
                visited.add(url)
                continue
            
            html_content, text_content, title, meta_desc, status_code = result
            
            # Save to database
            page = ScrapedPage(
                audit_job_id=job_id,
                url=url,
                domain=domain,
                is_target=is_target,
                html_content=html_content,
                text_content=text_content,
                title=title,
                meta_description=meta_desc,
                status_code=status_code,
                content_type="text/html",
                word_count=len(text_content.split()),
                url_hash=url_hash,
            )
            
            self.db.add(page)
            try:
                await self.db.commit()
            except IntegrityError:
                await self.db.rollback()
                visited.add(url)
                continue
            
            visited.add(url)
            pages_scraped += 1
            
            # Track priority pages
            if self.identify_page_priority(url) <= 2:
                priority_urls.append(url)
            
            # Extract more links (only for target, with limit)
            if is_target and pages_scraped < max_pages:
                new_links = await self.extract_links(html_content, url, debug)
                for link in sorted(new_links, key=lambda x: self.identify_page_priority(x))[:30]:
                    if link not in visited:
                        to_visit.add(link)
            
            # Small delay
            await asyncio.sleep(0.2)
        
        print(f"[SCRAPE] Done: {pages_scraped} pages, {len(priority_urls)} priority")
        return pages_scraped, priority_urls, debug
    
    async def scrape_job(self, job_id: str) -> Tuple[int, List[str], ScrapeDebug]:
        """
        Scrape all domains for a job
        Returns: (total_pages, priority_urls, target_debug)
        """
        result = await self.db.execute(
            select(AuditJob).where(AuditJob.id == job_id)
        )
        job = result.scalar_one_or_none()
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        # Update status
        job.status = "scraping"
        job.current_stage = "scraping_target"
        job.scraping_started_at = datetime.utcnow()
        job.progress_percent = 10
        await self.db.commit()
        await asyncio.sleep(0.3)  # Give frontend time to display this stage
        
        total_scraped = 0
        all_priority_urls = []
        target_debug = None
        
        # Scrape target domain
        print(f"[SCRAPE] === Starting target domain: {job.target_domain} ===")
        target_scraped, target_priority, target_debug = await self.scrape_domain(
            job.target_domain,
            job_id,
            is_target=True,
            max_pages=settings.max_pages_target,
        )
        total_scraped += target_scraped
        all_priority_urls.extend(target_priority)
        
        # Save debug info immediately
        job.scrape_debug = target_debug.to_dict()
        await self.db.commit()
        
        print(f"[SCRAPE] Target done: {target_scraped} pages")
        
        # Update progress
        job.progress_percent = 40
        job.current_stage = "scraping_competitors"
        await self.db.commit()
        await asyncio.sleep(0.3)  # Give frontend time to display this stage
        
        # Scrape competitors (only if target succeeded)
        if target_scraped > 0 and job.competitor_domains:
            for i, competitor in enumerate(job.competitor_domains):
                if not competitor.strip():
                    continue
                print(f"[SCRAPE] Starting competitor {i+1}: {competitor}")
                comp_scraped, _, _ = await self.scrape_domain(
                    competitor,
                    job_id,
                    is_target=False,
                    max_pages=settings.max_pages_competitor,
                )
                total_scraped += comp_scraped
                print(f"[SCRAPE] Competitor done: {comp_scraped} pages")
                
                progress = 40 + int((i + 1) / len(job.competitor_domains) * 20)
                job.progress_percent = min(progress, 60)
                await self.db.commit()
        
        # Mark scraping complete
        job.scraping_completed_at = datetime.utcnow()
        job.total_pages_scraped = total_scraped
        job.progress_percent = 60
        await self.db.commit()
        
        print(f"[SCRAPE] === Complete: {total_scraped} total pages ===")
        return total_scraped, all_priority_urls, target_debug
