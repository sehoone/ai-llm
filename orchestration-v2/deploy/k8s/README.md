# K8s 배포 (이중화)

docker-compose 기반 단일 노드 배포를 Kubernetes HA 구성으로 전환한 매니페스트 모음입니다.

## 디렉터리 구조

```
k8s/
├── namespace.yaml
├── config/
│   ├── configmap.yaml          # 비민감 설정 (PostgreSQL 호스트명 등)
│   └── secrets.example.yaml    # Secret 구조 예시 (직접 적용 금지)
├── data/
│   ├── postgres/               # CloudNativePG — primary 1 + replica 1
│   ├── redis/                  # Redis 3-pod StatefulSet + Sentinel 사이드카
│   ├── clickhouse/             # ClickHouse StatefulSet
│   └── minio/                  # MinIO 4-pod distributed StatefulSet
├── app/
│   ├── platform/               # Spring Boot  replicas:2  HPA·PDB 포함
│   ├── orchestrator/           # FastAPI       replicas:2  HPA·PDB 포함
│   └── admin-front/            # Next.js       replicas:2  HPA 포함
├── langfuse/                   # Langfuse v3   replicas:2
├── ingress/                    # NGINX Ingress (WebSocket/SSE 분리)
├── observability/
│   ├── prometheus/
│   ├── grafana/
│   └── cadvisor/               # DaemonSet
└── scripts/
    ├── deploy.sh               # 전체 배포
    ├── stop.sh                 # 중지 / 삭제
    ├── logs.sh                 # 로그 조회
    ├── create-secrets.sh       # .env → K8s Secret
    └── init-minio.sh           # MinIO 버킷 초기화
```

## 사전 요구사항

| 항목 | 버전 |
|------|------|
| Kubernetes | 1.28+ |
| kubectl | 클러스터와 동일 버전 |
| envsubst | gettext 패키지 포함 |
| StorageClass `fast-ssd` | 클러스터에 존재해야 함 — 없으면 yaml 에서 변경 |

## 빠른 시작

```bash
# 1. 이미지 빌드 & 레지스트리 푸시 (각 서비스 Dockerfile 기준)
docker build -t your-registry.io/llm-platform/platform-server:v1.0 ../platform-server
docker build -t your-registry.io/llm-platform/orchestrator-server:v1.0 ../orchestrator-server
docker build -t your-registry.io/llm-platform/admin-front:v1.0 ../admin-front
docker push your-registry.io/llm-platform/platform-server:v1.0
# ... (나머지 동일)

# 2. 전체 배포
cd deploy/k8s/scripts
REGISTRY=your-registry.io/llm-platform TAG=v1.0 ./deploy.sh staging

# 3. 로그 확인
./logs.sh orchestrator staging

# 4. 중지 (볼륨 보존)
./stop.sh staging

# 5. 전체 삭제 (볼륨 포함)
./stop.sh staging --delete --with-data
```

## StorageClass 변경

클러스터의 StorageClass 이름이 `fast-ssd` 가 아닌 경우:

```bash
# 일괄 변경 (예: standard 로 변경)
grep -r "fast-ssd" . --include="*.yaml" -l | \
  xargs sed -i 's/storageClassName: fast-ssd/storageClassName: standard/g'
```

## pgvector 이미지 설정

`data/postgres/cluster.yaml` 의 `imageName` 은 pgvector 미포함 기본 이미지입니다.  
pgvector 를 사용하려면 커스텀 이미지를 빌드해 교체하세요:

```dockerfile
# deploy/k8s/data/postgres/Dockerfile
FROM ghcr.io/cloudnative-pg/postgresql:16.3
USER root
RUN apt-get update && apt-get install -y postgresql-16-pgvector && rm -rf /var/lib/apt/lists/*
USER postgres
```

```bash
docker build -t your-registry.io/llm-platform/postgresql-pgvector:16 deploy/k8s/data/postgres/
# cluster.yaml imageName 을 위 이미지로 변경
```

## 도메인 설정

`ingress/ingress.yaml` 에서 `your-domain.com` 을 실제 도메인으로 변경하세요:

```yaml
- host: your-domain.com
```

## 주요 이중화 포인트

| 서비스 | 전략 | 비고 |
|--------|------|------|
| platform / orchestrator | replicas:2 + PodAntiAffinity + HPA | 다른 노드에 배치 |
| admin-front | replicas:2 + PodAntiAffinity | |
| PostgreSQL | CloudNativePG primary+replica | 자동 failover ~30초 |
| Redis | 3-pod StatefulSet + Sentinel 사이드카 | quorum:2 |
| MinIO | 4-pod distributed mode | erasure coding 활성화 |

## 트러블슈팅

| 증상 | 확인 사항 |
|------|-----------|
| platform pod CrashLoopBackOff | `kubectl logs deploy/platform -n llm-platform` — DB 연결·JWT_SECRET_KEY 확인 |
| CloudNativePG cluster not ready | `kubectl describe cluster postgres-ha -n llm-platform` — StorageClass 존재 여부 |
| Redis sentinel 연결 실패 | `kubectl exec redis-0 -n llm-platform -- redis-cli -p 26379 sentinel masters` |
| Ingress 404 | `kubectl get ingress -n llm-platform` — host 필드 도메인 확인 |
| envsubst: command not found | `brew install gettext` (macOS) / `apt install gettext-base` (Ubuntu) |
