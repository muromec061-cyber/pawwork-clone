    chmod +x "$WORKSPACE/bot/agent_router.py"
    log "ROUTER" "Agent Router created вњ“ ({len(AGENTS)} agents registered)" 
    
    # РЎС‡РёС‚Р°РµРј РєРѕР»РёС‡РµСЃС‚РІРѕ Р·Р°СЂРµРіРёСЃС‚СЂРёСЂРѕРІР°РЅРЅС‹С… Р°РіРµРЅС‚РѕРІ
    local count=$(grep -c "register(" "$WORKSPACE/bot/agent_router.py")
    log "ROUTER" "Registered $count agents total"
}

# в”Ђв”Ђв”Ђ Р“Р»Р°РІРЅС‹Р№ Р·Р°РїСѓСЃРє в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
main() {
    install_python
    install_agent_frameworks
    install_dev_tools
    install_heavy_agents
    install_node_agents
    install_gold_miner
    create_agent_router
    
    log "DONE" "=== ALL AGENTS INSTALLED ==="
    log "DONE" "РџСЂРѕРІРµСЂСЊ Р»РѕРі: $LOG"
    
    # РС‚РѕРі
    echo ""
    echo "в•”в•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•—"
    echo "в•‘     ALL 30+ AGENTS INSTALLED вњ“           в•‘"
    echo "в• в•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•Ј"
    echo "в•‘  РСЃРїРѕР»СЊР·СѓР№ Telegram Р±РѕС‚Р°:                в•‘"
    echo "в•‘  /agents вЂ” СЃРїРёСЃРѕРє РІСЃРµС… Р°РіРµРЅС‚РѕРІ           в•‘"
    echo "в•‘  /crewai <Р·Р°РїСЂРѕСЃ> вЂ” CrewAI               в•‘"
    echo "в•‘  /autogen <Р·Р°РїСЂРѕСЃ> вЂ” AutoGen             в•‘"
    echo "в•‘  /openclaw <Р·Р°РїСЂРѕСЃ> вЂ” OpenClaw           в•‘"
    echo "в•‘  /gold вЂ” GitHub Gold Miner               в•‘"
    echo "в•‘  /ai <Р·Р°РїСЂРѕСЃ> вЂ” Р°РІС‚Рѕ-РІС‹Р±РѕСЂ Р°РіРµРЅС‚Р°        в•‘"
    echo "в•љв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ќ"
}

main

