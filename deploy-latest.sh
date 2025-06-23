#!/bin/bash

# GitHub Container Registry の latest イメージをデプロイ
# namespace: satomichi

echo "🚀 Deploying latest images from GitHub Container Registry..."

# 方法1: kubectl apply でデプロイメント全体を適用
echo "📦 Applying Kubernetes deployments..."
kubectl apply -f k8s/backend-deployment.yaml && kubectl apply -f k8s/frontend-deployment.yaml

# 方法2: イメージの強制更新（より高速）
echo "🔄 Force updating container images..."
kubectl set image deployment/backend backend=ghcr.io/satomichi/observability_practice-backend:latest -n satomichi && \
kubectl set image deployment/frontend frontend=ghcr.io/satomichi/observability_practice-frontend:latest -n satomichi

# ロールアウト状況の確認
echo "⏳ Waiting for rollout to complete..."
kubectl rollout status deployment/backend -n satomichi && \
kubectl rollout status deployment/frontend -n satomichi

echo "✅ Deployment completed!"

# Pod の状況確認
echo "📊 Current pod status:"
kubectl get pods -n satomichi -l app=backend,app=frontend 
