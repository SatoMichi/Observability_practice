# ビルドステージ
FROM node:18-alpine AS build
WORKDIR /app

# 依存関係のインストール（キャッシュ最適化）
COPY package*.json ./
RUN npm ci --only=production --no-audit --no-fund

# ソースコードのコピーとビルド
COPY . .
RUN npm run build

# プロダクションステージ（最軽量）
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"] 
