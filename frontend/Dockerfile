# FX Trading System Frontend Dockerfile
# マルチステージビルド

# ビルドステージ
FROM node:18-alpine AS builder

WORKDIR /app

# package.jsonとpackage-lock.jsonをコピー
COPY package*.json ./

# 依存関係のインストール
RUN npm ci --only=production

# ソースコードをコピー
COPY . .

# Next.js アプリケーションのビルド
RUN npm run build

# 実行ステージ
FROM node:18-alpine AS runner

WORKDIR /app

# 非rootユーザーの作成
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# 必要なファイルのコピー
COPY --from=builder /app/public ./public

# 自動的にproduction用のファイルを出力してもらうため、next.config.jsでoutput: 'standalone'を設定
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# 非rootユーザーに切り替え
USER nextjs

# ポート公開
EXPOSE 3000

# 環境変数設定
ENV PORT 3000
ENV NODE_ENV production

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:3000/api/health || exit 1

# アプリケーション起動
CMD ["node", "server.js"]