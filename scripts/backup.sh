#!/bin/bash
#
# 数据库和媒体文件备份脚本
# 用于生产环境定时备份
#
# 使用方法:
#   ./scripts/backup.sh [options]
#
# 选项:
#   -d, --database     仅备份数据库
#   -m, --media        仅备份媒体文件
#   -a, --all          备份所有(默认)
#   -h, --help         显示帮助信息
#
# 定时任务配置(crontab -e):
#   每天凌晨2点执行完整备份:
#   0 2 * * * /path/to/scripts/backup.sh -a >> /var/log/backup.log 2>&1
#
#   每小时备份一次数据库:
#   0 * * * * /path/to/scripts/backup.sh -d >> /var/log/backup.log 2>&1
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/social_media}"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=${RETENTION_DAYS:-30}

DB_USER=${DB_USER:-postgres}
DB_PASSWORD=${DB_PASSWORD:-postgres}
DB_NAME=${DB_NAME:-social_media}
DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-5432}

DOWNLOADS_DIR="${PROJECT_DIR}/downloads"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1" >&2
}

check_dependencies() {
    local missing=()
    
    if ! command -v docker &> /dev/null; then
        missing+=("docker")
    fi
    
    if ! command -v gzip &> /dev/null; then
        missing+=("gzip")
    fi
    
    if [ ${#missing[@]} -ne 0 ]; then
        error "Missing required dependencies: ${missing[*]}"
        exit 1
    fi
}

create_backup_dir() {
    if [ ! -d "$BACKUP_DIR" ]; then
        mkdir -p "$BACKUP_DIR"
        log "Created backup directory: $BACKUP_DIR"
    fi
}

backup_database() {
    log "Starting database backup..."
    
    local backup_file="${BACKUP_DIR}/db_${DATE}.sql.gz"
    
    docker exec social_media_postgres pg_dump -U "$DB_USER" -d "$DB_NAME" --clean --if-exists | gzip > "$backup_file"
    
    if [ $? -eq 0 ]; then
        local size=$(du -h "$backup_file" | cut -f1)
        log "Database backup completed: $backup_file (Size: $size)"
    else
        error "Database backup failed"
        rm -f "$backup_file"
        return 1
    fi
}

backup_media() {
    log "Starting media files backup..."
    
    if [ ! -d "$DOWNLOADS_DIR" ]; then
        log "Downloads directory not found, skipping media backup"
        return 0
    fi
    
    local backup_file="${BACKUP_DIR}/media_${DATE}.tar.gz"
    local file_count=$(find "$DOWNLOADS_DIR" -type f | wc -l)
    
    if [ "$file_count" -eq 0 ]; then
        log "No media files to backup"
        return 0
    fi
    
    tar -czf "$backup_file" -C "$(dirname "$DOWNLOADS_DIR")" "$(basename "$DOWNLOADS_DIR")"
    
    if [ $? -eq 0 ]; then
        local size=$(du -h "$backup_file" | cut -f1)
        log "Media backup completed: $backup_file (Files: $file_count, Size: $size)"
    else
        error "Media backup failed"
        rm -f "$backup_file"
        return 1
    fi
}

cleanup_old_backups() {
    log "Cleaning up backups older than $RETENTION_DAYS days..."
    
    local deleted_count=0
    
    while IFS= read -r file; do
        rm -f "$file"
        ((deleted_count++))
    done < <(find "$BACKUP_DIR" -name "*.gz" -type f -mtime +$RETENTION_DAYS)
    
    if [ $deleted_count -gt 0 ]; then
        log "Deleted $deleted_count old backup(s)"
    else
        log "No old backups to delete"
    fi
}

show_usage() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -d, --database     Backup database only"
    echo "  -m, --media        Backup media files only"
    echo "  -a, --all          Backup all (default)"
    echo "  -h, --help         Show this help message"
    echo ""
    echo "Environment variables:"
    echo "  BACKUP_DIR         Backup directory (default: /var/backups/social_media)"
    echo "  RETENTION_DAYS     Days to keep backups (default: 30)"
    echo "  DB_USER            Database user (default: postgres)"
    echo "  DB_PASSWORD        Database password (default: postgres)"
    echo "  DB_NAME            Database name (default: social_media)"
}

main() {
    local backup_type="all"
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -d|--database)
                backup_type="database"
                shift
                ;;
            -m|--media)
                backup_type="media"
                shift
                ;;
            -a|--all)
                backup_type="all"
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    check_dependencies
    create_backup_dir
    
    log "========================================"
    log "Starting backup (Type: $backup_type)"
    log "========================================"
    
    case $backup_type in
        database)
            backup_database
            ;;
        media)
            backup_media
            ;;
        all)
            backup_database
            backup_media
            ;;
    esac
    
    cleanup_old_backups
    
    log "========================================"
    log "Backup completed"
    log "========================================"
}

main "$@"
