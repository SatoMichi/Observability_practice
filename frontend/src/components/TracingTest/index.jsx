import { useState } from 'react';
import { getTracer } from '../../tracing.js';
import './index.scss';

function TracingTest() {
  const [testResults, setTestResults] = useState([]);
  const tracer = getTracer();

  const runSimpleTest = () => {
    const span = tracer.startSpan('test_simple_action', {
      attributes: {
        'test.type': 'simple',
        'test.timestamp': Date.now(),
        'user.action': 'button_click'
      }
    });

    setTimeout(() => {
      span.setAttributes({
        'test.result': 'success',
        'test.duration': '100ms'
      });
      span.end();
      
      setTestResults(prev => [...prev, {
        id: Date.now(),
        type: 'Simple Test',
        traceId: span.traceId,
        spanId: span.spanId,
        timestamp: new Date().toLocaleTimeString()
      }]);
    }, 100);
  };

  const runErrorTest = () => {
    const span = tracer.startSpan('test_error_handling', {
      attributes: {
        'test.type': 'error',
        'test.timestamp': Date.now()
      }
    });

    try {
      // 意図的なエラー
      throw new Error('This is a test error for tracing');
    } catch (error) {
      span.recordException(error);
      span.setStatus('ERROR');
      span.end();
      
      setTestResults(prev => [...prev, {
        id: Date.now(),
        type: 'Error Test',
        traceId: span.traceId,
        spanId: span.spanId,
        timestamp: new Date().toLocaleTimeString(),
        error: error.message
      }]);
    }
  };

  const clearResults = () => {
    setTestResults([]);
  };

  return (
    <div className="tracing-test">
      <h3>🧪 Tracing & Datadog RUM Test</h3>
      <div className="test-controls">
        <button onClick={runSimpleTest} className="test-btn success">
          シンプルテスト実行
        </button>
        <button onClick={runErrorTest} className="test-btn error">
          エラーテスト実行
        </button>
        <button onClick={clearResults} className="test-btn clear">
          結果クリア
        </button>
      </div>
      
      <div className="test-results">
        <h4>テスト結果:</h4>
        {testResults.length === 0 ? (
          <p>まだテストが実行されていません</p>
        ) : (
          <ul>
            {testResults.map(result => (
              <li key={result.id} className={result.error ? 'error' : 'success'}>
                <strong>{result.type}</strong> - {result.timestamp}
                <br />
                <small>
                  Trace ID: {result.traceId}
                  <br />
                  Span ID: {result.spanId}
                  {result.error && (
                    <>
                      <br />
                      Error: {result.error}
                    </>
                  )}
                </small>
              </li>
            ))}
          </ul>
        )}
      </div>
      
      <div className="instructions">
        <h4>📝 確認方法:</h4>
        <ol>
          <li>ブラウザの開発者ツール（F12）を開く</li>
          <li>コンソールタブを確認</li>
          <li>テストボタンをクリック</li>
          <li>🌐や🐕のログでトレース情報を確認</li>
        </ol>
      </div>
    </div>
  );
}

export default TracingTest; 
