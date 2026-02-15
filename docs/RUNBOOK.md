# Operational Runbook

## Health Checks

```bash
# Service health
curl http://<gateway-ip>:8080/health
curl http://<auth-ip>:5000/health

# Kubernetes
kubectl get pods -n <namespace>
kubectl top pods -n <namespace>
```

## Common Issues

### 1. Gateway returns 503
**Symptom:** `/health` returns `{"status": "unhealthy"}`
**Check:** Which dependency is down (MongoDB or RabbitMQ)?
```bash
kubectl logs deployment/gateway -n <namespace> --tail=50
kubectl get svc mongodb rabbitmq -n <namespace>
```
**Fix:** Restart the affected infrastructure pod or check PVC status.

### 2. Converter not processing videos
**Symptom:** Videos uploaded but no MP3 generated
**Check:**
```bash
# Check RabbitMQ queue depth
curl -u guest:guest http://<rabbitmq-ip>:15672/api/queues

# Check converter logs
kubectl logs deployment/converter -n <namespace> --tail=100
```
**Fix:** Scale up converter or check for OOM kills (`kubectl describe pod`).

### 3. Emails not being sent
**Symptom:** Conversion completes but no email received
**Check:**
```bash
kubectl logs deployment/notification -n <namespace> --tail=50
```
**Common causes:**
- Invalid SMTP credentials (check `GMAIL_ADDRESS`, `GMAIL_PASSWORD` secrets)
- App password not configured in Gmail
- Queue backlog — check RabbitMQ `mp3` queue

## Scaling

```bash
# Manual scaling
kubectl scale deployment/converter --replicas=5 -n <namespace>

# Check HPA status
kubectl get hpa -n <namespace>

# Check current resource usage
kubectl top pods -n <namespace>
```

## Rollback

```bash
# Helm rollback
helm history video-converter -n <namespace>
helm rollback video-converter <revision> -n <namespace>

# Kubernetes rollback
kubectl rollout undo deployment/gateway -n <namespace>
kubectl rollout status deployment/gateway -n <namespace>
```

## Disaster Recovery

### Database Backup (MySQL)
```bash
kubectl exec -it statefulset/mysql -n <namespace> -- \
  mysqldump -u root -p auth > backup_$(date +%Y%m%d).sql
```

### Database Backup (MongoDB)
```bash
kubectl exec -it statefulset/mongodb -n <namespace> -- \
  mongodump --out /tmp/backup_$(date +%Y%m%d)
```

## Monitoring Alerts

| Metric | Threshold | Action |
|--------|----------|--------|
| Error rate > 5% | Warning | Check gateway logs |
| Error rate > 15% | Critical | Roll back last deployment |
| Queue depth > 100 | Warning | Scale up converter |
| Queue depth > 500 | Critical | Investigate converter failures |
| Pod restarts > 3 | Warning | Check OOM / probe failures |
| Disk usage > 80% | Critical | Clean old files or expand PVC |
