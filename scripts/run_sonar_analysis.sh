#!/bin/bash
# 本地SonarQube代码分析脚本
# 用法: ./run_sonar_analysis.sh [项目Key]

# 设置默认值和颜色
PROJECT_KEY=${1:-"local-project"}
PROJECT_NAME=${PROJECT_KEY}
SONAR_CONTAINER="sonarqube"
SONAR_PORT=9000
SONAR_URL="http://localhost:${SONAR_PORT}"
ADMIN_PASSWORD="adminPassword123!"
TOKEN_NAME="local-analysis-token"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 函数定义
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

wait_for_sonarqube() {
    log_info "等待SonarQube启动..."
    local retries=0
    local max_retries=30
    
    while [ $retries -lt $max_retries ]; do
        if curl -s -f -X GET "${SONAR_URL}/api/system/status" | grep -q "UP"; then
            log_success "SonarQube服务已启动"
            return 0
        fi
        retries=$((retries+1))
        log_info "尝试 $retries/$max_retries - 仍在等待..."
        sleep 10
    done
    
    log_error "等待SonarQube启动超时"
    return 1
}

# 检查Docker是否已安装
if ! command -v docker &> /dev/null; then
    log_error "未安装Docker。请先安装Docker后再运行此脚本。"
fi

# 1. 检查是否已有SonarQube容器在运行
if docker ps -a | grep -q ${SONAR_CONTAINER}; then
    log_info "检测到SonarQube容器已存在"
    if docker ps | grep -q ${SONAR_CONTAINER}; then
        log_info "SonarQube容器已在运行"
    else
        log_info "重新启动SonarQube容器..."
        if ! docker start ${SONAR_CONTAINER}; then
            log_error "启动SonarQube容器失败"
        fi
    fi
else
    log_info "创建并启动SonarQube容器..."
    if ! docker run -d --name ${SONAR_CONTAINER} -e SONAR_ES_BOOTSTRAP_CHECKS_DISABLE=true -p ${SONAR_PORT}:9000 sonarqube:latest; then
        log_error "创建SonarQube容器失败"
    fi
    log_success "SonarQube容器已创建"
fi

# 2. 等待SonarQube启动
wait_for_sonarqube

# 3. 尝试使用默认密码登录，如果成功则更改密码
if curl -s -u admin:admin "${SONAR_URL}/api/system/ping" | grep -q "pong"; then
    log_info "使用默认密码登录成功，正在更改密码..."
    curl -s -X POST -u admin:admin "${SONAR_URL}/api/users/change_password?login=admin&previousPassword=admin&password=${ADMIN_PASSWORD}" > /dev/null
    log_success "密码已更改"
else
    log_info "已经更改过密码，使用现有密码继续"
fi

# 4. 创建令牌
log_info "创建分析令牌..."
TOKEN=$(curl -s -X POST -u admin:${ADMIN_PASSWORD} "${SONAR_URL}/api/user_tokens/generate?name=${TOKEN_NAME}" | grep -o '"token":"[^"]*"' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    # 尝试获取现有令牌
    log_warning "创建令牌失败，可能已存在同名令牌，尝试重新生成..."
    # 删除旧令牌
    curl -s -X POST -u admin:${ADMIN_PASSWORD} "${SONAR_URL}/api/user_tokens/revoke?name=${TOKEN_NAME}" > /dev/null
    # 创建新令牌
    TOKEN=$(curl -s -X POST -u admin:${ADMIN_PASSWORD} "${SONAR_URL}/api/user_tokens/generate?name=${TOKEN_NAME}" | grep -o '"token":"[^"]*"' | cut -d'"' -f4)
    
    if [ -z "$TOKEN" ]; then
        log_error "无法生成分析令牌"
    fi
fi

log_success "令牌已生成: ${TOKEN}"

# 5. 创建或更新项目
log_info "创建项目 ${PROJECT_KEY}..."
curl -s -X POST -u admin:${ADMIN_PASSWORD} "${SONAR_URL}/api/projects/create?name=${PROJECT_NAME}&project=${PROJECT_KEY}" > /dev/null
log_success "项目已创建/更新"

# 6. 运行分析
log_info "开始代码分析..."
docker run --rm --network=host \
    -v $(pwd):/usr/src \
    sonarsource/sonar-scanner-cli \
    -Dsonar.projectKey=${PROJECT_KEY} \
    -Dsonar.projectName=${PROJECT_NAME} \
    -Dsonar.sources=src \
    -Dsonar.tests=tests \
    -Dsonar.host.url=${SONAR_URL} \
    -Dsonar.token=${TOKEN}

log_success "分析完成！ 查看结果: ${SONAR_URL}/dashboard?id=${PROJECT_KEY}"
echo ""
log_info "提示："
echo "  - 要停止SonarQube容器: docker stop ${SONAR_CONTAINER}"
echo "  - 要删除SonarQube容器: docker rm ${SONAR_CONTAINER}"
echo ""
log_info "您可能需要针对特定项目结构调整分析参数"