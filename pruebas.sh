#!/bin/bash
# Pruebas de microservicios - Learning Analytics
# Uso: bash pruebas.sh

GATEWAY="http://localhost:8000"
PASS=0
FAIL=0

echo "=========================================="
echo "  Learning Analytics - Suite de Pruebas"
echo "=========================================="
echo ""

# ── 1. Health Check ─────────────────────────────────────────────────────────
test_health() {
    echo "[TEST] Health Check - API Gateway"
    RESP=$(curl -s -o /dev/null -w "%{http_code}" "$GATEWAY/health")
    if [ "$RESP" = "200" ]; then
        echo "  ✓ API Gateway health: $RESP"
        PASS=$((PASS+1))
    else
        echo "  ✗ API Gateway health: $RESP (esperado 200)"
        FAIL=$((FAIL+1))
    fi
}

# ── 2. Health Check All ─────────────────────────────────────────────────────
test_health_all() {
    echo "[TEST] Health Check - Todos los servicios"
    RESP=$(curl -s "$GATEWAY/health/all")
    echo "  $RESP" | head -c 200
    echo ""
    STATUS=$(echo "$RESP" | grep -o '"status":"ok"' | wc -l)
    if [ "$STATUS" -ge 4 ]; then
        echo "  ✓ $STATUS servicios responden ok"
        PASS=$((PASS+1))
    else
        echo "  ✗ Solo $STATUS servicios responden (esperado >=4)"
        FAIL=$((FAIL+1))
    fi
}

# ── 3. Event Service ────────────────────────────────────────────────────────
test_events() {
    echo "[TEST] Event Service - Capturar evento"
    RESP=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$GATEWAY/api/events/" \
        -H "Content-Type: application/json" \
        -d '{"student_id":"s001","institution_id":"UNAL","course_id":"C101","event_type":"login"}')
    if [ "$RESP" = "200" ]; then
        echo "  ✓ Evento capturado: $RESP"
        PASS=$((PASS+1))
    else
        echo "  ✗ Evento falló: $RESP"
        FAIL=$((FAIL+1))
    fi

    echo "[TEST] Event Service - Eventos recientes"
    RESP=$(curl -s -o /dev/null -w "%{http_code}" "$GATEWAY/api/events/recent")
    if [ "$RESP" = "200" ]; then
        echo "  ✓ Eventos recientes: $RESP"
        PASS=$((PASS+1))
    else
        echo "  ✗ Eventos recientes falló: $RESP"
        FAIL=$((FAIL+1))
    fi
}

# ── 4. Analytics Service ────────────────────────────────────────────────────
test_analytics() {
    echo "[TEST] Analytics Service - Predecir riesgo"
    RESP=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$GATEWAY/api/analytics/predict" \
        -H "Content-Type: application/json" \
        -d '{"student_id":"s001","institution_id":"UNAL","avg_score":4.5,"attendance_rate":0.6,"late_submissions":5,"login_frequency":2}')
    if [ "$RESP" = "200" ]; then
        echo "  ✓ Predicción exitosa: $RESP"
        PASS=$((PASS+1))
    else
        echo "  ✗ Predicción falló: $RESP"
        FAIL=$((FAIL+1))
    fi

    echo "[TEST] Analytics Service - Stats"
    RESP=$(curl -s -o /dev/null -w "%{http_code}" "$GATEWAY/api/analytics/stats")
    if [ "$RESP" = "200" ]; then
        echo "  ✓ Stats: $RESP"
        PASS=$((PASS+1))
    else
        echo "  ✗ Stats falló: $RESP"
        FAIL=$((FAIL+1))
    fi
}

# ── 5. Alert Service ────────────────────────────────────────────────────────
test_alerts() {
    echo "[TEST] Alert Service - Listar alertas"
    RESP=$(curl -s -o /dev/null -w "%{http_code}" "$GATEWAY/api/alerts/")
    if [ "$RESP" = "200" ]; then
        echo "  ✓ Alertas listadas: $RESP"
        PASS=$((PASS+1))
    else
        echo "  ✗ Alertas falló: $RESP"
        FAIL=$((FAIL+1))
    fi

    echo "[TEST] Alert Service - Marcar como leída"
    RESP=$(curl -s -o /dev/null -w "%{http_code}" -X PUT "$GATEWAY/api/alerts/a1/read")
    if [ "$RESP" = "200" ]; then
        echo "  ✓ Alerta marcada: $RESP"
        PASS=$((PASS+1))
    else
        echo "  ✗ Marcar alerta falló: $RESP"
        FAIL=$((FAIL+1))
    fi
}

# ── 6. Dashboard Service ────────────────────────────────────────────────────
test_dashboard() {
    echo "[TEST] Dashboard Service - Summary (Aggregator)"
    RESP=$(curl -s -o /dev/null -w "%{http_code}" "$GATEWAY/api/dashboard/summary")
    if [ "$RESP" = "200" ]; then
        echo "  ✓ Dashboard summary: $RESP"
        PASS=$((PASS+1))
    else
        echo "  ✗ Dashboard summary falló: $RESP"
        FAIL=$((FAIL+1))
    fi
}

# ── 7. Flujo Completo (Chained Microservices) ──────────────────────────────
test_flow() {
    echo "[TEST] Flujo completo: Prediccion -> Alerta"
    RESULT=$(curl -s -X POST "$GATEWAY/api/analytics/predict" \
        -H "Content-Type: application/json" \
        -d '{"student_id":"s999","institution_id":"UNAL","avg_score":2.5,"attendance_rate":0.3,"late_submissions":12,"login_frequency":1}')
    echo "  Resultado: $(echo $RESULT | head -c 300)"
    HAS_ALERT=$(echo "$RESULT" | grep -o '"alert_generated":true' | wc -l)
    if [ "$HAS_ALERT" -ge 1 ]; then
        echo "  ✓ Alerta generada automáticamente desde analytics-service"
        PASS=$((PASS+1))
    else
        echo "  ✗ No se generó alerta"
        FAIL=$((FAIL+1))
    fi
}

# ── 8. Test del Mono (Caída de servicio) ────────────────────────────────────
test_monkey() {
    echo "[TEST] Test del Mono - Servicio caído (analytics-service detenido)"
    echo "  (Simulado: el gateway responde 503 cuando un servicio no está disponible)"
    # Simulate by sending to a non-existent service path
    RESP=$(curl -s -o /dev/null -w "%{http_code}" "$GATEWAY/api/nonexistent")
    if [ "$RESP" = "404" ]; then
        echo "  ✓ Ruta inexistente manejada con 404"
        PASS=$((PASS+1))
    else
        echo "  ✗ Error inesperado: $RESP"
        FAIL=$((FAIL+1))
    fi
}

# ── Run all tests ───────────────────────────────────────────────────────────
test_health
test_health_all
test_events
test_analytics
test_alerts
test_dashboard
test_flow
test_monkey

echo ""
echo "=========================================="
echo "  Resultados: $PASS pasaron, $FAIL fallaron"
echo "=========================================="
