/**
 * Simple OpenTelemetry Tracing Setup for Frontend
 * フロントエンド用のシンプルなOpenTelemetryトレース設定
 * + Datadog RUM統合
 */

import { trace } from '@opentelemetry/api';
import { datadogRum } from '@datadog/browser-rum';

/**
 * 簡易版のトレーサー実装
 * APIライブラリのみを使用して手動でSpanを管理
 */
class SimpleFrontendTracer {
  constructor() {
    this.serviceName = 'gutenberg-search-frontend';
    this.currentSpans = new Map();
    this.isDatadogEnabled = false;
  }

  /**
   * Datadog RUMの初期化（開発用設定）
   */
  initializeDatadogRUM() {
    try {
      // 開発環境用の設定（実際のプロダクションでは環境変数から取得）
      const config = {
        applicationId: import.meta.env.VITE_DD_APPLICATION_ID || 'dev-test-app',
        clientToken: import.meta.env.VITE_DD_CLIENT_TOKEN || 'dev-test-token',
        site: import.meta.env.VITE_DD_SITE || 'datadoghq.com',
        service: import.meta.env.VITE_DD_SERVICE || 'gutenberg-search-frontend',
        env: import.meta.env.VITE_DD_ENV || 'development',
        version: import.meta.env.VITE_DD_VERSION || '1.0.0',
        sampleRate: parseInt(import.meta.env.VITE_DD_SAMPLE_RATE || '100'),
        trackInteractions: true,
        defaultPrivacyLevel: 'mask-user-input',
        allowedTracingOrigins: [
          'http://localhost:8000', // バックエンドAPI
          window.location.origin   // 同一オリジン
        ],
        enableExperimentalFeatures: ['trace-init']
      };

      // 開発環境でのテスト用：実際のDatadogアカウントがない場合はモック
      if (config.clientToken === 'dev-test-token') {
        console.log('🧪 Datadog RUM - Development Mode (Mock)');
        console.log('   Config:', config);
        console.log('   ⚠️  実際のDatadog送信は行われません');
        this.isDatadogEnabled = false;
        return;
      }

      datadogRum.init(config);
      this.isDatadogEnabled = true;
      
      console.log('🐕 Datadog RUM initialized successfully');
      console.log('   Service:', config.service);
      console.log('   Environment:', config.env);
      
    } catch (error) {
      console.warn('⚠️  Datadog RUM initialization failed:', error);
      console.log('   Continuing with OpenTelemetry-only mode...');
      this.isDatadogEnabled = false;
    }
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

    // Datadog RUMへの統合
    if (this.isDatadogEnabled && datadogRum) {
      try {
        datadogRum.addAction(name, {
          'custom.trace_id': traceId,
          'custom.span_id': spanId,
          'custom.service': this.serviceName,
          ...span.attributes
        });
        console.log(`🐕 Datadog RUM Action created: ${name}`);
      } catch (error) {
        console.warn('⚠️  Datadog RUM action creation failed:', error);
      }
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
    return Math.random().toString(16).slice(2, 18).padStart(16, '0');
  }

  generateTraceId() {
    return Math.random().toString(16).slice(2, 34).padStart(32, '0');
  }
  
  /**
   * W3C Trace Context準拠のtraceparentヘッダーを生成
   * Format: version-trace_id-parent_id-trace_flags
   * 例: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
   */
  generateTraceParent(traceId, spanId) {
    const version = '00';
    const traceFlags = '01'; // sampled
    
    // デバッグログを削除（本番環境用）
    // console.log(`🔧 generateTraceParent called with:`, { traceId, spanId });
    
    return `${version}-${traceId}-${spanId}-${traceFlags}`;
  }
}

// グローバルトレーサーインスタンス
let globalTracer = null;

/**
 * OpenTelemetryの初期化 + Datadog RUM統合
 */
export function initializeTracing() {
  globalTracer = new SimpleFrontendTracer();
  
  // Datadog RUMの初期化
  globalTracer.initializeDatadogRUM();
  
  // Fetchの自動計装（分散トレース対応版）
  if (typeof window !== 'undefined' && window.fetch) {
    const originalFetch = window.fetch;
    
    window.fetch = async function(url, options = {}) {
      // 新しいSpanを直接作成してIDを取得
      const spanId = globalTracer.generateSpanId();
      const traceId = globalTracer.generateTraceId();
      
      const span = {
        name: 'http_request',
        spanId: spanId,
        traceId: traceId,
        startTime: Date.now(),
        endTime: null,
        attributes: {
          'http.method': options.method || 'GET',
          'http.url': url.toString(),
          'component': 'fetch'
        },
        status: 'OK'
      };

      globalTracer.currentSpans.set(spanId, span);
      
      console.log(`🌐 Frontend Span Started: http_request`);
      console.log(`   Service: ${globalTracer.serviceName}`);
      console.log(`   Trace ID: ${traceId}`);
      console.log(`   Span ID: ${spanId}`);

      try {
        // W3C Trace Context ヘッダーを生成（直接値を使用）
        const traceparent = globalTracer.generateTraceParent(traceId, spanId);
        
        // リクエストヘッダーにトレースコンテキストを追加
        const headers = {
          ...options.headers,
          'traceparent': traceparent,
          'tracestate': `frontend=true,service=${globalTracer.serviceName}`
        };
        
        console.log(`🔗 Distributed Trace Header: ${traceparent}`);
        console.log(`   Trace ID: ${traceId}`);
        console.log(`   Span ID: ${spanId}`);
        
        const response = await originalFetch(url, {
          ...options,
          headers
        });
        
        // Spanに属性を追加
        span.attributes['http.status_code'] = response.status;
        span.attributes['http.status_text'] = response.statusText;
        span.attributes['http.response.success'] = response.ok;
        span.attributes['distributed.trace.propagated'] = true;

        return response;
      } catch (error) {
        span.status = 'ERROR';
        span.attributes['error.name'] = error.name;
        span.attributes['error.message'] = error.message;
        throw error;
      } finally {
        // Spanを終了
        span.endTime = Date.now();
        const duration = span.endTime - span.startTime;
        
        console.log(`🌐 Frontend Span Ended: http_request`);
        console.log(`   Duration: ${duration}ms`);
        console.log(`   Status: ${span.status}`);
        console.log('');
        
        globalTracer.sendSpanToCollector(span, duration);
        globalTracer.currentSpans.delete(spanId);
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

