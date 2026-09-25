# Docker + Kubernetes Web Demo

一个零第三方依赖的最小 Web 示例，用于练习 Docker 镜像打包和 Kubernetes 部署。

## 包含内容

- `GET /`：展示页面，页面加载后会自动调用接口。
- `GET /api/hello`：返回应用、版本、Pod、节点和当前时间等信息。
- `GET /healthz`：存活检查。
- `GET /readyz`：就绪检查。
- `Dockerfile`：基于 Python 3.12 slim，使用非 root 用户运行。
- `docker-compose.yml`：本地容器快速验证。
- `k8s/`：Namespace、ConfigMap、Deployment、Service、Ingress。

## 目录结构

```text
docker-k8s-web-demo/
├── app.py
├── templates/
│   └── index.html
├── Dockerfile
├── .dockerignore
├── docker-compose.yml
├── README.md
└── k8s/
    ├── namespace.yaml
    ├── configmap.yaml
    ├── deployment.yaml
    ├── service.yaml
    ├── ingress.yaml
    └── kustomization.yaml
```

## 1. 本地运行（可选）

有 Python 3.11+ 时可以直接运行，不需要安装依赖：

```powershell
python app.py
Invoke-RestMethod http://localhost:18080/api/hello
```

浏览器访问 <http://localhost:18080>。如果本机命令名不是 `python`，请使用已安装 Python 的实际路径。

## 2. Docker 打包与运行

```powershell
docker build --build-arg APP_VERSION=1.0.0 -t web-demo:1.0.0 .
docker run --rm -p 18080:18080 --name web-demo web-demo:1.0.0
```

验证：

```powershell
Invoke-RestMethod http://localhost:18080/api/hello
docker inspect --format "{{.State.Health.Status}}" web-demo
```

使用 Compose：

```powershell
docker compose up --build
docker compose down
```

## 3. 部署到 Kubernetes

先确保 `kubectl` 能连接到集群。以下命令适合 Docker Desktop Kubernetes、kind 或 minikube 等本地练习集群。

```powershell
docker build --build-arg APP_VERSION=1.0.0 -t web-demo:1.0.0 .
kubectl apply -k .\k8s
kubectl -n web-demo get pods,service,ingress
kubectl -n web-demo rollout status deployment/web-demo
```

本地集群可能需要在启动 Pod 前载入镜像：

```powershell
# kind
kind load docker-image web-demo:1.0.0

# minikube
minikube image load web-demo:1.0.0
```

### 访问方式 A：port-forward（最稳定）

```powershell
kubectl -n web-demo port-forward service/web-demo 18080:80
```

浏览器访问 <http://localhost:18080>，接口地址是 <http://localhost:18080/api/hello>。

### 访问方式 B：NodePort

清单已将 NodePort 固定为 `30080`：

```text
http://localhost:30080
http://localhost:30080/api/hello
```

如果本地环境没有把 NodePort 映射到 `localhost`：

```powershell
# minikube
minikube service -n web-demo web-demo --url

# kind：kind 默认不会直接把 NodePort 暴露给宿主机
# 可先用 port-forward，或配置 kind 的 extraPortMappings
```

### 访问方式 C：Ingress（可选）

前提是集群已安装 ingress-nginx。将域名解析到 Ingress 控制器地址：

```text
127.0.0.1 web-demo.local
```

然后访问 <http://web-demo.local>。不同集群的 ingress-nginx 地址可能不同，真实服务器应把这个域名解析到负载均衡器公网地址。

## 4. 观察 Kubernetes 行为

```powershell
kubectl -n web-demo get pods -o wide --watch
kubectl -n web-demo logs deployment/web-demo --tail=50
kubectl -n web-demo describe deployment web-demo

# 滚动更新
docker build --build-arg APP_VERSION=1.0.1 -t web-demo:1.0.1 .
kubectl -n web-demo set image deployment/web-demo web=web-demo:1.0.1
kubectl -n web-demo rollout status deployment/web-demo
kubectl -n web-demo rollout history deployment/web-demo

# 回滚
kubectl -n web-demo rollout undo deployment/web-demo
```

页面中的 `pod` 字段会随负载均衡切换到不同副本而变化，可用来观察 Service 转发。

## 5. 清理

```powershell
kubectl delete -k .\k8s
docker rm -f web-demo
```

## 推送到镜像仓库

真实集群无法直接读取本机镜像时，先把镜像推到仓库：

```powershell
docker tag web-demo:1.0.0 <registry>/<namespace>/web-demo:1.0.0
docker push <registry>/<namespace>/web-demo:1.0.0
kubectl -n web-demo set image deployment/web-demo web=<registry>/<namespace>/web-demo:1.0.0
```

部署清单默认使用 `imagePullPolicy: IfNotPresent`，适合本地载入镜像。如果镜像仓库需要鉴权，请在目标命名空间创建 `imagePullSecrets` 并在 Deployment 中引用。
