/**
 * Simple OpenTelemetry Tracing Setup for Frontend
 * フロントエンド用のシンプルなOpenTelemetryトレース設定
 */

import { trace } from '@opentelemetry/api';

/**
 * 簡易版のトレーサー実装
 * APIライブラリのみを使用して手動でSpanを管理
 */
class SimpleFrontendTracer {
  constructor() {
    this.serviceName = 'gutenberg-search-frontend';
    this.currentSpans = new Map();
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
      // OpenTelemetry OTLP format風のデータ構造
      const otlpSpan = {
        resourceSpans: [{
          resource: {
            attributes: [
              { key: 'service.name', value: { stringValue: this.serviceName }},
              { key: 'service.version', value: { stringValue: '1.0.0' }},
              { key: 'deployment.environment', value: { stringValue: 'development' }}
            ]
          },
          instrumentationLibrarySpans: [{
            instrumentationLibrary: {
              name: 'frontend-manual-tracer',
              version: '1.0.0'
            },
            spans: [{
              traceId: span.traceId,
              spanId: span.spanId,
              name: span.name,
              kind: 'SPAN_KIND_CLIENT',
              startTimeUnixNano: span.startTime * 1000000,
              endTimeUnixNano: span.endTime * 1000000,
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

      // バックエンドの専用エンドポイントに送信（今後実装予定）
      // 現在はコンソールに出力のみ
      console.log('📤 Sending span to collector (simulation):', {
        service: this.serviceName,
        span: span.name,
        traceId: span.traceId,
        duration: duration
      });
      
    } catch (error) {
      console.warn('Failed to send span to collector:', error);
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
      span.status = 'ERROR';
      span.attributes['error.name'] = error.name;
      span.attributes['error.message'] = error.message;
      span.attributes['error.stack'] = error.stack;
    }
  }

  setStatus(spanId, status) {
    const span = this.currentSpans.get(spanId);
    if (span) {
      span.status = status;
    }
  }

  generateSpanId() {
    return Math.random().toString(16).slice(2, 18);
  }

  generateTraceId() {
    return Math.random().toString(16).slice(2, 34);
  }
}

// グローバルトレーサーインスタンス
let globalTracer = null;

/**
 * OpenTelemetryの初期化
 */
export function initializeTracing() {
  globalTracer = new SimpleFrontendTracer();
  
  // Fetchの自動計装（シンプル版）
  if (typeof window !== 'undefined' && window.fetch) {
    const originalFetch = window.fetch;
    
    window.fetch = async function(url, options = {}) {
      const span = globalTracer.startSpan('http_request', {
        attributes: {
          'http.method': options.method || 'GET',
          'http.url': url.toString(),
          'component': 'fetch'
        }
      });

      try {
        const response = await originalFetch(url, options);
        
        span.setAttributes({
          'http.status_code': response.status,
          'http.status_text': response.statusText,
          'http.response.success': response.ok
        });

        return response;
      } catch (error) {
        span.recordException(error);
        throw error;
      } finally {
        span.end();
      }
    };
  }

  console.log('🚀 Simple OpenTelemetry Frontend Tracing initialized');
  
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
        end: () => {},
        setAttributes: () => {},
        recordException: () => {},
        setStatus: () => {}
      })
    };
  }
  return globalTracer;
} 

