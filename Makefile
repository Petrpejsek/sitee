.PHONY: dev stop logs clean help

help:
	@echo "LLM Audit Engine - Dev Commands"
	@echo ""
	@echo "  make dev     - Start all services (one command!)"
	@echo "  make stop    - Stop all services"
	@echo "  make logs    - Tail all logs"
	@echo "  make clean   - Clean up (stop + remove data)"
	@echo ""

dev:
	@chmod +x dev.sh
	@./dev.sh

stop:
	@chmod +x dev-stop.sh
	@./dev-stop.sh

logs:
	@echo "📊 Tailing logs (Ctrl+C to exit)..."
	@tail -f logs/*.log 2>/dev/null || echo "No logs yet"

clean: stop
	@echo "🧹 Cleaning up..."
	@docker-compose down -v
	@rm -rf backend/venv backend/reports logs
	@echo "✅ Clean"


