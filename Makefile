.PHONY: test-l3 help up down logs restart status fix-apparmor fix-port fix-perms setup-venv

# デフォルトのヘルプ表示
help:
	@echo "=================================================="
	@echo "🤖 Kanon Core Operation Console (GPD & Mac)"
	@echo "=================================================="
	@echo "【基本操作】"
	@echo "  make up             - 実機コンテナをビルドしてバックグラウンド起動します"
	@echo "  make down           - 実機コンテナを安全に停止・削除します"
	@echo "  make logs           - コンテナの実行ログをリアルタイム表示します"
	@echo "  make restart        - コンテナを再起動します"
	@echo "  make status         - コンテナおよびポートの使用状況を表示します"
	@echo ""
	@echo "【トラブルシューティング用ツール】"
	@echo "  make fix-apparmor   - AppArmorのブロックを解除し停止エラーを解消します (sudo要)"
	@echo "  make fix-port       - ポート 5000 を占有しているゾンビプロセスを強制解放します"
	@echo "  make fix-perms      - stateディレクトリのパーミッションエラーを解決します (sudo要)"
	@echo "  make setup-venv     - python-venvが足りない場合の環境構築を行います"
	@echo ""
	@echo "【テスト関連】"
	@echo "  make test-l3        - L3シミュレーションテストを実行します"
	@echo "=================================================="

# L3テスト
test-l3:
	python3 ai-agent/workspace/tests/run_l3_simulation.py

# 実機コンテナの起動
up:
	docker compose -f ai-agent/docker-compose.yml --env-file ai-agent/secrets/.env up -d --build

# 実機コンテナの停止
down:
	docker compose -f ai-agent/docker-compose.yml --env-file ai-agent/secrets/.env down

# ログ確認
logs:
	docker logs -f ai_agent_core

# 再起動
restart:
	docker compose -f ai-agent/docker-compose.yml --env-file ai-agent/secrets/.env restart

# ステータス確認
status:
	@docker ps -a
	@echo ""
	@echo "--- Port 5000 binding status ---"
	@sudo lsof -i :5000 || echo "Port 5000 is free."

# AppArmorのブロック解決
fix-apparmor:
	sudo aa-remove-unknown

# ポート競合の解決
fix-port:
	@echo "Force releasing port 5000..."
	@sudo kill -9 $$(sudo lsof -t -i:5000) 2>/dev/null || echo "No process found on port 5000"

# パーミッションエラーの解決
fix-perms:
	sudo chown -R $$(whoami):$$(whoami) ai-agent/workspace/state

# 仮想環境の自動構築
setup-venv:
	sudo apt install -y python3-venv || sudo apt install -y python3.14-venv
	python3 -m venv ai-agent/workspace/.venv
	./ai-agent/workspace/.venv/bin/pip install -r ai-agent/workspace/requirements.txt
