#!/usr/bin/env fish

function sonar-ai-fix
    set -l options (fish_opt --short=h --long=help)
    set options $options (fish_opt --short=p --long=pr --required-val)
    set options $options (fish_opt --short=o --long=output --required-val)
    
    argparse $options -- $argv
    
    # 显示帮助信息
    if set -q _flag_help
        echo "用法: sonar-ai-fix [选项]"
        echo ""
        echo "选项:"
        echo "  -h, --help            显示帮助信息"
        echo "  -p, --pr PR_NUMBER    获取特定PR的SonarCloud报告"
        echo "  -o, --output PREFIX   设置输出文件名前缀 (默认: sonar)"
        echo ""
        echo "示例:"
        echo "  sonar-ai-fix              # 获取最新的SonarCloud报告"
        echo "  sonar-ai-fix --pr 42      # 获取PR #42的SonarCloud报告"
        echo "  sonar-ai-fix -o pr42      # 将输出文件保存为pr42_report.md和pr42_issues.json"
        return 0
    end
    
    # 设置输出文件名前缀
    set -l OUTPUT_PREFIX "sonar"
    if set -q _flag_output
        set OUTPUT_PREFIX $_flag_output
    end
    
    # 检查当前目录是否是项目目录
    if not test -f "pyproject.toml"; or not test -d "src/mcp_dbutils"
        echo "错误: 请在项目根目录运行此命令"
        echo "当前目录不是mcp-dbutils项目目录"
        return 1
    end
    
    # 下载最新的构件
    echo "正在下载 SonarCloud 分析报告..."
    
    # 获取工作流运行ID
    set -l RUN_ID
    
    if set -q _flag_pr
        echo "获取PR #$_flag_pr的SonarCloud报告..."
        set RUN_ID (gh run list --workflow "Quality Assurance" --branch "pull/$_flag_pr/head" --limit 1 --json databaseId --jq '.[0].databaseId')
    else
        echo "获取最新的SonarCloud报告..."
        set RUN_ID (gh run list --workflow "Quality Assurance" --limit 1 --json databaseId --jq '.[0].databaseId')
    end
    
    if test -z "$RUN_ID"
        echo "错误: 无法获取工作流运行ID"
        return 1
    else
        echo "RUN_ID: $RUN_ID"
    end
    
    # 创建临时目录存放下载的文件
    set TEMP_DIR (mktemp -d)
    
    # 下载构件
    gh run download $RUN_ID --name sonarcloud-issues --dir $TEMP_DIR
    
    if test $status -ne 0
        echo "错误: 下载构件失败"
        rm -rf $TEMP_DIR
        return 1
    end
    
    # 检查文件是否存在
    if not test -f "$TEMP_DIR/sonar_report.md"
        echo "错误: 未找到 sonar_report.md 文件"
        rm -rf $TEMP_DIR
        return 1
    end
    
    if not test -f "$TEMP_DIR/sonar_issues.json"
        echo "错误: 未找到 sonar_issues.json 文件"
        rm -rf $TEMP_DIR
        return 1
    end
    
    # 复制文件到当前目录
    set -l REPORT_FILE "$OUTPUT_PREFIX"_report.md
    set -l ISSUES_FILE "$OUTPUT_PREFIX"_issues.json
    
    cp "$TEMP_DIR/sonar_report.md" ./$REPORT_FILE
    cp "$TEMP_DIR/sonar_issues.json" ./$ISSUES_FILE
    
    # 清理临时目录
    rm -rf $TEMP_DIR
    
    echo "已下载 SonarCloud 分析报告:"
    echo "- $REPORT_FILE: Markdown格式的报告，适合人类阅读"
    echo "- $ISSUES_FILE: JSON格式的原始数据，适合AI处理"
    echo ""
    echo "使用方法:"
    echo "1. 查看报告: cat $REPORT_FILE"
    echo "2. 提供给AI: 将$REPORT_FILE的内容复制给AI，请求修复建议"
    echo "3. 高级分析: 将$ISSUES_FILE提供给AI进行更深入的分析"
end
