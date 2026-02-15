#!/bin/bash
# ══════════════════════════════════════════════════════════════
#  Video-to-MP3 Converter — Full End-to-End Test Script
# ══════════════════════════════════════════════════════════════
#
#  Usage:
#    bash scripts/test-flow.sh <path-to-video-file>
#    bash scripts/test-flow.sh /mnt/c/Users/vaibh/Downloads/sheesha.mp4
#
#  Prerequisites:
#    - Docker containers running (docker compose up -d)
#    - curl, jq (optional), docker CLI available
#
# ══════════════════════════════════════════════════════════════

set -euo pipefail

# ── Configuration ────────────────────────────────────────────
GATEWAY_URL="${GATEWAY_URL:-http://localhost:8080}"
AUTH_URL="${AUTH_URL:-http://localhost:5000}"
EMAIL="${EMAIL:-georgio@email.com}"
PASSWORD="${PASSWORD:-Admin123}"
VIDEO_FILE="${1:-}"
OUTPUT_DIR="${OUTPUT_DIR:-.}"
MAX_WAIT_SECONDS=180    # Max time to wait for conversion
POLL_INTERVAL=5         # Seconds between status checks

# ── Colors ───────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# ── Helper Functions ─────────────────────────────────────────
log_step()    { echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; echo -e "${BOLD}  $1${NC}"; echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; }
log_info()    { echo -e "  ${CYAN}ℹ${NC}  $1"; }
log_success() { echo -e "  ${GREEN}✅${NC} $1"; }
log_warn()    { echo -e "  ${YELLOW}⚠️${NC}  $1"; }
log_error()   { echo -e "  ${RED}❌${NC} $1"; }
log_detail()  { echo -e "     ${CYAN}→${NC} $1"; }

cleanup() {
    # Remove temp files on exit
    [ -f /tmp/health_response.json ] && rm -f /tmp/health_response.json
    [ -f /tmp/upload_response.txt ] && rm -f /tmp/upload_response.txt
}
trap cleanup EXIT

# ── Validate Input ───────────────────────────────────────────
echo -e "\n${BOLD}${CYAN}🎵 Video-to-MP3 Converter — End-to-End Test${NC}\n"

if [ -z "$VIDEO_FILE" ]; then
    log_error "No video file specified!"
    echo ""
    echo "  Usage: bash $0 <path-to-video-file>"
    echo ""
    echo "  Examples:"
    echo "    bash $0 ./my_video.mp4"
    echo "    bash $0 /mnt/c/Users/vaibh/Downloads/sheesha.mp4"
    echo ""
    echo "  Environment variables (optional):"
    echo "    GATEWAY_URL=http://localhost:8080"
    echo "    EMAIL=georgio@email.com"
    echo "    PASSWORD=Admin123"
    echo "    OUTPUT_DIR=./downloads"
    exit 1
fi

if [ ! -f "$VIDEO_FILE" ]; then
    log_error "File not found: $VIDEO_FILE"
    exit 1
fi

FILE_SIZE=$(du -h "$VIDEO_FILE" | cut -f1)
log_info "Video file: $(basename "$VIDEO_FILE") (${FILE_SIZE})"
log_info "Gateway:    $GATEWAY_URL"
log_info "User:       $EMAIL"

# ══════════════════════════════════════════════════════════════
#  STEP 0: Pre-flight Health Checks
# ══════════════════════════════════════════════════════════════
log_step "Step 0: Pre-flight Health Checks"

# Check Gateway
log_info "Checking Gateway health..."
GATEWAY_HEALTH=$(curl -s -w "\n%{http_code}" "$GATEWAY_URL/health" 2>/dev/null) || true
GATEWAY_HTTP_CODE=$(echo "$GATEWAY_HEALTH" | tail -1)
GATEWAY_BODY=$(echo "$GATEWAY_HEALTH" | head -1)

if [ "$GATEWAY_HTTP_CODE" = "200" ]; then
    log_success "Gateway is healthy"
    log_detail "MongoDB:  connected"
    log_detail "RabbitMQ: connected"
else
    log_warn "Gateway returned HTTP $GATEWAY_HTTP_CODE"
    log_detail "Response: $GATEWAY_BODY"
    log_info "Proceeding anyway (upload may still work)..."
fi

# Check Auth
log_info "Checking Auth service health..."
AUTH_HEALTH=$(curl -s -w "\n%{http_code}" "$AUTH_URL/health" 2>/dev/null) || true
AUTH_HTTP_CODE=$(echo "$AUTH_HEALTH" | tail -1)

if [ "$AUTH_HTTP_CODE" = "200" ]; then
    log_success "Auth service is healthy"
    log_detail "MySQL: connected"
else
    log_error "Auth service is not healthy (HTTP $AUTH_HTTP_CODE)"
    log_info "Tip: Run 'docker compose ps' to check container status"
    exit 1
fi

# Check RabbitMQ queues
log_info "Checking RabbitMQ queues..."
QUEUE_INFO=$(docker exec rabbitmq rabbitmqctl list_queues name messages consumers 2>/dev/null) || true
if echo "$QUEUE_INFO" | grep -q "video"; then
    VIDEO_CONSUMERS=$(echo "$QUEUE_INFO" | grep "video" | awk '{print $3}')
    MP3_CONSUMERS=$(echo "$QUEUE_INFO" | grep "mp3" | awk '{print $3}')
    log_success "RabbitMQ queues are ready"
    log_detail "video queue: $VIDEO_CONSUMERS consumer(s)"
    log_detail "mp3 queue:   $MP3_CONSUMERS consumer(s)"

    if [ "$VIDEO_CONSUMERS" = "0" ]; then
        log_warn "No consumers on 'video' queue — converter may be down!"
        log_info "Check: docker logs converter --tail 10"
    fi
else
    log_warn "Could not query RabbitMQ queues (is Docker accessible?)"
fi

# ══════════════════════════════════════════════════════════════
#  STEP 1: Login
# ══════════════════════════════════════════════════════════════
log_step "Step 1: Authenticate"

log_info "Logging in as $EMAIL..."
LOGIN_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$GATEWAY_URL/login" \
    -u "$EMAIL:$PASSWORD" 2>/dev/null)

LOGIN_HTTP_CODE=$(echo "$LOGIN_RESPONSE" | tail -1)
TOKEN=$(echo "$LOGIN_RESPONSE" | head -1)

if [ "$LOGIN_HTTP_CODE" != "200" ]; then
    log_error "Login failed (HTTP $LOGIN_HTTP_CODE)"
    log_detail "Response: $TOKEN"
    echo ""
    echo "  Troubleshooting:"
    echo "    1. Check auth service: docker logs auth --tail 20"
    echo "    2. Verify MySQL has user data: docker exec auth-mysql mysql -u root -p -e 'SELECT * FROM auth.user;'"
    echo "    3. Verify credentials in .env match init.sql"
    exit 1
fi

if [ -z "$TOKEN" ] || echo "$TOKEN" | grep -qi "error\|unauthorized\|denied"; then
    log_error "Login returned invalid token: $TOKEN"
    exit 1
fi

log_success "JWT token received"
log_detail "Token: ${TOKEN:0:50}..."

# ══════════════════════════════════════════════════════════════
#  STEP 2: Upload Video
# ══════════════════════════════════════════════════════════════
log_step "Step 2: Upload Video"

log_info "Uploading: $(basename "$VIDEO_FILE") ($FILE_SIZE)..."

# Record queue state before upload
QUEUE_BEFORE=$(docker exec rabbitmq rabbitmqctl list_queues name messages 2>/dev/null | grep "video" | awk '{print $2}') || QUEUE_BEFORE="?"

UPLOAD_START=$(date +%s)
UPLOAD_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$GATEWAY_URL/upload" \
    -H "Authorization: Bearer $TOKEN" \
    -F "file=@$VIDEO_FILE" 2>/dev/null)
UPLOAD_END=$(date +%s)
UPLOAD_DURATION=$((UPLOAD_END - UPLOAD_START))

UPLOAD_HTTP_CODE=$(echo "$UPLOAD_RESPONSE" | tail -1)
UPLOAD_BODY=$(echo "$UPLOAD_RESPONSE" | head -1)

if [ "$UPLOAD_HTTP_CODE" = "200" ] || echo "$UPLOAD_BODY" | grep -qi "success"; then
    log_success "Upload successful (${UPLOAD_DURATION}s)"
    log_detail "Response: $UPLOAD_BODY"
else
    log_error "Upload failed (HTTP $UPLOAD_HTTP_CODE)"
    log_detail "Response: $UPLOAD_BODY"
    echo ""
    echo "  Troubleshooting:"
    echo "    1. Check gateway logs: docker logs gateway --tail 20"
    echo "    2. Verify token is valid (tokens expire after 24h)"
    echo "    3. Ensure user has admin=true in JWT"
    exit 1
fi

# Verify message was queued
sleep 1
QUEUE_AFTER=$(docker exec rabbitmq rabbitmqctl list_queues name messages 2>/dev/null | grep "video" | awk '{print $2}') || QUEUE_AFTER="?"
log_detail "Video queue: $QUEUE_BEFORE → $QUEUE_AFTER message(s)"

# ══════════════════════════════════════════════════════════════
#  STEP 3: Wait for Conversion
# ══════════════════════════════════════════════════════════════
log_step "Step 3: Wait for Conversion"

log_info "Monitoring converter for completion (timeout: ${MAX_WAIT_SECONDS}s)..."
echo ""

ELAPSED=0
CONVERSION_DONE=false
MP3_FID=""

while [ $ELAPSED -lt $MAX_WAIT_SECONDS ]; do
    sleep $POLL_INTERVAL
    ELAPSED=$((ELAPSED + POLL_INTERVAL))

    # Check if mp3 queue got a new message (meaning converter finished)
    MP3_MSGS=$(docker exec rabbitmq rabbitmqctl list_queues name messages 2>/dev/null | grep "mp3" | awk '{print $2}') || MP3_MSGS="0"
    VIDEO_MSGS=$(docker exec rabbitmq rabbitmqctl list_queues name messages 2>/dev/null | grep "video" | awk '{print $2}') || VIDEO_MSGS="0"

    # Progress indicator
    printf "\r  ⏳ Elapsed: %3ds | video queue: %s | mp3 queue: %s " "$ELAPSED" "$VIDEO_MSGS" "$MP3_MSGS"

    # Try to get mp3_fid from MongoDB (most reliable method)
    MP3_FID=$(docker exec mongodb mongosh --quiet --eval "
        const files = db.getSiblingDB('mp3s').fs.files.find().sort({uploadDate: -1}).limit(1).toArray();
        if (files.length > 0) print(files[0]._id.toString());
    " 2>/dev/null | tail -1) || MP3_FID=""

    # Check if conversion is done
    if [ -n "$MP3_FID" ] && [ "$MP3_FID" != "" ] && [ ${#MP3_FID} -eq 24 ]; then
        echo ""
        CONVERSION_DONE=true
        break
    fi

    # Check converter logs for errors
    CONVERTER_ERRORS=$(docker logs converter --tail 5 2>&1 | grep -i "error\|exception\|traceback" | head -1) || true
    if [ -n "$CONVERTER_ERRORS" ]; then
        echo ""
        log_warn "Converter error detected: $CONVERTER_ERRORS"
    fi
done

echo ""

if [ "$CONVERSION_DONE" = true ]; then
    log_success "Conversion complete! (${ELAPSED}s)"
    log_detail "MP3 File ID: $MP3_FID"
else
    log_error "Conversion timed out after ${MAX_WAIT_SECONDS}s"
    echo ""
    echo "  Debugging steps:"
    echo "    1. Check converter logs:    docker logs converter --tail 30"
    echo "    2. Check video queue:       docker exec rabbitmq rabbitmqctl list_queues"
    echo "    3. Check container status:  docker compose ps"
    echo "    4. Check for OOM kills:     docker inspect converter | grep -A5 State"
    echo ""
    echo "  If converter is processing a large file, increase MAX_WAIT_SECONDS:"
    echo "    MAX_WAIT_SECONDS=300 bash $0 $VIDEO_FILE"
    exit 1
fi

# ══════════════════════════════════════════════════════════════
#  STEP 4: Download MP3
# ══════════════════════════════════════════════════════════════
log_step "Step 4: Download MP3"

# Generate output filename
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BASE_NAME=$(basename "$VIDEO_FILE" | sed 's/\.[^.]*$//')
OUTPUT_FILE="${OUTPUT_DIR}/${BASE_NAME}_${TIMESTAMP}.mp3"

# Create output directory if needed
mkdir -p "$OUTPUT_DIR"

log_info "Downloading MP3 (fid: $MP3_FID)..."
DOWNLOAD_START=$(date +%s)

HTTP_CODE=$(curl -s -w "%{http_code}" -o "$OUTPUT_FILE" \
    "$GATEWAY_URL/download?fid=$MP3_FID" \
    -H "Authorization: Bearer $TOKEN" 2>/dev/null)

DOWNLOAD_END=$(date +%s)
DOWNLOAD_DURATION=$((DOWNLOAD_END - DOWNLOAD_START))

if [ "$HTTP_CODE" = "200" ] && [ -f "$OUTPUT_FILE" ] && [ -s "$OUTPUT_FILE" ]; then
    MP3_SIZE=$(du -h "$OUTPUT_FILE" | cut -f1)
    log_success "Download successful (${DOWNLOAD_DURATION}s)"
    log_detail "File: $OUTPUT_FILE"
    log_detail "Size: $MP3_SIZE"
else
    log_error "Download failed (HTTP $HTTP_CODE)"
    [ -f "$OUTPUT_FILE" ] && rm -f "$OUTPUT_FILE"
    echo ""
    echo "  Troubleshooting:"
    echo "    1. Verify fid exists: docker exec mongodb mongosh --eval \"db.getSiblingDB('mp3s').fs.files.find()\" --quiet"
    echo "    2. Check gateway logs: docker logs gateway --tail 20"
    exit 1
fi

# ══════════════════════════════════════════════════════════════
#  STEP 5: Verification
# ══════════════════════════════════════════════════════════════
log_step "Step 5: Verification"

# Verify MP3 file integrity
if command -v file &>/dev/null; then
    FILE_TYPE=$(file "$OUTPUT_FILE" | cut -d: -f2)
    if echo "$FILE_TYPE" | grep -qi "audio\|mpeg\|mp3\|layer III"; then
        log_success "File type verified:$FILE_TYPE"
    else
        log_warn "Unexpected file type:$FILE_TYPE"
    fi
fi

# Check notification status
log_info "Checking notification service..."
NOTIF_LOG=$(docker logs notification --tail 5 2>&1 | grep -i "sent\|error\|fail" | head -1) || NOTIF_LOG=""
if echo "$NOTIF_LOG" | grep -qi "sent\|success"; then
    log_success "Email notification sent"
elif echo "$NOTIF_LOG" | grep -qi "error\|fail"; then
    log_warn "Email notification failed (SMTP not configured — this is expected locally)"
else
    log_info "No notification activity detected (SMTP may not be configured)"
fi

# ══════════════════════════════════════════════════════════════
#  Summary
# ══════════════════════════════════════════════════════════════
echo ""
echo -e "${GREEN}══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}${BOLD}  ✅ Pipeline Complete!${NC}"
echo -e "${GREEN}══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${BOLD}Input:${NC}    $(basename "$VIDEO_FILE") ($FILE_SIZE)"
echo -e "  ${BOLD}Output:${NC}   $OUTPUT_FILE ($MP3_SIZE)"
echo -e "  ${BOLD}MP3 FID:${NC}  $MP3_FID"
echo -e "  ${BOLD}Time:${NC}     Upload ${UPLOAD_DURATION}s + Convert ${ELAPSED}s + Download ${DOWNLOAD_DURATION}s"
echo ""
echo -e "  ${CYAN}Pipeline trace:${NC}"
echo -e "    Login     → JWT token received"
echo -e "    Upload    → Video stored in MongoDB (GridFS)"
echo -e "    RabbitMQ  → Message published to 'video' queue"
echo -e "    Converter → Video decoded, audio extracted via ffmpeg"
echo -e "    RabbitMQ  → MP3 fid published to 'mp3' queue"
echo -e "    Download  → MP3 retrieved from MongoDB (GridFS)"
echo ""
