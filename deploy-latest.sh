#!/bin/bash

# GitHub Container Registry の latest イメージをデプロイ
# namespace: satomichi

echo "🚀 Deploying latest images from GitHub Container Registry..."

# 方法1: kubectl apply でデプロイメント全体を適用
echo "📦 Applying Kubernetes deployments..."
kubectl apply -f k8s/backend-deployment.yaml && kubectl apply -f k8s/frontend-deployment.yaml

# 方法2: デプロイメントの強制再起動（最新イメージを確実にプル）
echo "🔄 Force restarting deployments to pull latest images..."
kubectl rollout restart deployment/backend -n satomichi && \
kubectl rollout restart deployment/frontend -n satomichi

# ロールアウト状況の確認
echo "⏳ Waiting for rollout to complete..."
kubectl rollout status deployment/backend -n satomichi && \
kubectl rollout status deployment/frontend -n satomichi

echo "✅ Deployment completed!"

# Pod の状況確認
echo "📊 Current pod status:"
kubectl get pods -n satomichi 
