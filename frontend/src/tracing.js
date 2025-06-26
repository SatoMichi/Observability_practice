/**
 * Simple Frontend Tracing for Datadog APM
 * - APMトレースのみ（RUM不要）
 * - Datadog Agent OTLP エンドポイント経由
 * - セキュアな実装（認証情報不要）
 * - 分散トレース対応
 */
class SimpleFrontendTracer {
  constructor(serviceName = 'gutenberg-search-frontend') {
    this.serviceName = serviceName;
    this.currentSpans = new Map();
    
    console.log('🚀 Simple OpenTelemetry Frontend Tracing initialized');
    console.log('📤 Sending traces to Datadog Agent OTLP endpoint');
    console.log('🔒 APM-only mode (no browser credentials required)');
  }

  startSpan(name, options = {}) {
    const spanId = this.generateSpanId();
    const traceId = this.generateTraceId();
    const startTime = Date.now();
    
    const span = {
      name,
      spanId,
      traceId,
      startTime,
      endTime: null,
      attributes: options.attributes || {},
      status: 'OK'
    };

    this.currentSpans.set(spanId, span);
    
    // コンソールにトレース情報を出力
    console.log(`🌐 Frontend Span Started: ${name}`);
    console.log(`   Service: ${this.serviceName}`);
    console.log(`   Trace ID: ${traceId}`);
    console.log(`   Span ID: ${spanId}`);
    if (Object.keys(span.attributes).length > 0) {
      console.log(`   Attributes:`, span.attributes);
    }

    return {
      traceId: span.traceId,
      spanId: span.spanId,
      end: () => this.endSpan(spanId),
      setAttributes: (attrs) => this.setAttributes(spanId, attrs),
      recordException: (error) => this.recordException(spanId, error),
      setStatus: (status) => this.setStatus(spanId, status)
    };
  }

  endSpan(spanId) {
    const span = this.currentSpans.get(spanId);
    if (span) {
      span.endTime = Date.now();
      const duration = span.endTime - span.startTime;
      
      console.log(`🌐 Frontend Span Ended: ${span.name}`);
      console.log(`   Duration: ${duration}ms`);
      console.log(`   Status: ${span.status}`);
      console.log('');
      
      // OTLP-like データ送信（実際のプロダクションでは適切なOTLPエクスポーターを使用）
      this.sendSpanToCollector(span, duration);
      
      this.currentSpans.delete(spanId);
    }
  }

  async sendSpanToCollector(span, duration) {
    try {
      // OpenTelemetry OTLP format（Datadog Agent互換）
      const otlpSpan = {
        resourceSpans: [{
          resource: {
            attributes: [
              { key: 'service.name', value: { stringValue: this.serviceName }},
              { key: 'service.version', value: { stringValue: '1.0.0' }},
              { key: 'deployment.environment', value: { stringValue: 'development' }},
              { key: 'telemetry.sdk.name', value: { stringValue: 'opentelemetry' }},
              { key: 'telemetry.sdk.language', value: { stringValue: 'javascript' }},
              { key: 'telemetry.sdk.version', value: { stringValue: '1.0.0' }}
            ]
          },
          scopeSpans: [{
            scope: {
              name: 'frontend-manual-tracer',
              version: '1.0.0'
            },
            spans: [{
              traceId: span.traceId,
              spanId: span.spanId,
              name: span.name,
              kind: 'SPAN_KIND_CLIENT',
              startTimeUnixNano: (span.startTime * 1000000).toString(),
              endTimeUnixNano: (span.endTime * 1000000).toString(),
              attributes: Object.entries(span.attributes).map(([key, value]) => ({
                key,
                value: { stringValue: value.toString() }
              })),
              status: {
                code: span.status === 'OK' ? 'STATUS_CODE_OK' : 'STATUS_CODE_ERROR'
              }
            }]
          }]
        }]
      };

      // Datadog Agent OTLP HTTP エンドポイントに送信
      try {
        // K8s環境のDatadog AgentのOTLPエンドポイント
        const otlpEndpoint = 'http://datadog-agent.monitoring.svc.cluster.local:4318/v1/traces';
        
        // ローカル開発環境の場合は直接ポートフォワード経由
        const isDevelopment = window.location.hostname === 'localhost';
        const endpoint = isDevelopment 
          ? 'http://localhost:4318/v1/traces'  // ローカル開発用（要ポートフォワード）
          : otlpEndpoint; // K8s環境用
        
        const response = await fetch(endpoint, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(otlpSpan)
        });

        if (response.ok) {
          console.log('✅ Span successfully sent to Datadog Agent OTLP:', {
            service: this.serviceName,
            span: span.name,
            traceId: span.traceId.substring(0, 8) + '...',
            duration: duration,
            endpoint: endpoint
          });
        } else {
          console.warn('⚠️ Failed to send span to Datadog Agent:', response.status, response.statusText);
        }
      } catch (networkError) {
        console.warn('⚠️ Network error sending to Datadog Agent:', networkError.message);
        
        // フォールバック：セキュアなローカルログ
        const safeLogData = {
          service: this.serviceName,
          span: span.name,
          traceId: span.traceId.substring(0, 8) + '...',
          duration: duration,
          status: 'local_fallback'
        };
        
        console.log('📤 Span data (local fallback):', safeLogData);
      }
      
    } catch (error) {
      console.warn('Failed to process span:', error);
    }
  }

  setAttributes(spanId, attributes) {
    const span = this.currentSpans.get(spanId);
    if (span) {
      Object.assign(span.attributes, attributes);
    }
  }

  recordException(spanId, error) {
    const span = this.currentSpans.get(spanId);
    if (span) {
      span.attributes['error.message'] = error.message;
      span.attributes['error.name'] = error.name;
      span.status = 'ERROR';
    }
  }

  setStatus(spanId, status) {
    const span = this.currentSpans.get(spanId);
    if (span) {
      span.status = status;
    }
  }

  generateSpanId() {
    return Array.from(crypto.getRandomValues(new Uint8Array(8)), b => b.toString(16).padStart(2, '0')).join('');
  }

  generateTraceId() {
    return Array.from(crypto.getRandomValues(new Uint8Array(16)), b => b.toString(16).padStart(2, '0')).join('');
  }

  /**
   * W3C Trace Context準拠のtraceparentヘッダーを生成
   * 分散トレース用（フロントエンド→バックエンド）
   */
  generateTraceParent(traceId, spanId) {
    const version = '00';
    const traceFlags = '01'; // sampled
    return `${version}-${traceId}-${spanId}-${traceFlags}`;
  }
}

// グローバルトレーサーインスタンス
let globalTracer = null;

/**
 * トレーシングシステムの初期化
 */
export function initializeTracing() {
  if (!globalTracer) {
    globalTracer = new SimpleFrontendTracer();
  }
  return globalTracer;
}

/**
 * 手動でSpanを作成するためのヘルパー関数
 */
export function createSpan(name, fn, attributes = {}) {
  if (!globalTracer) {
    console.warn('Tracer not initialized. Call initializeTracing() first.');
    return fn();
  }

  const span = globalTracer.startSpan(name, { attributes });
  
  try {
    const result = fn();
    if (result && typeof result.then === 'function') {
      // Promiseの場合
      return result
        .then(res => {
          span.end();
          return res;
        })
        .catch(err => {
          span.recordException(err);
          span.end();
          throw err;
        });
    } else {
      // 同期処理の場合
      span.end();
      return result;
    }
  } catch (error) {
    span.recordException(error);
    span.end();
    throw error;
  }
}

/**
 * グローバルトレーサーを取得
 */
export function getTracer() {
  if (!globalTracer) {
    console.warn('Tracer not initialized. Call initializeTracing() first.');
      return {
    startSpan: () => ({
      traceId: 'unknown',
      spanId: 'unknown',
      end: () => {},
      setAttributes: () => {},
      recordException: () => {},
      setStatus: () => {}
    })
  };
  }
  return globalTracer;
} 

