# 검색 성능 최적화 변경사항

## 문제점 정의

### 1. 의도적인 성능 병목점
- `slow_tfidf_search` 함수가 Observability 교육용으로 의도적으로 느리게 구현됨
- 5만 번의 불필요한 문자열 처리 루프
- 200ms 의도적 지연
- 10번 중복 벡터화 처리
- 5번 유사도 계산 재실행
- 스니펫 생성 시 30ms 지연

### 2. 제한된 검색 옵션
- 프론트엔드에서 `slow_tfidf`만 선택 가능
- 빠른 검색 방법(`tfidf`, `bm25`) 비활성화

## 변경사항

### Frontend 수정
**파일**: `frontend/src/components/SearchForm/index.jsx`

```javascript
// 변경 전
<option value="slow_tfidf">TF-IDF</option>

// 변경 후  
<option value="tfidf">TF-IDF（従来手法）</option>
<option value="bm25">BM25（高精度）</option>
<option value="slow_tfidf">遅いTF-IDF（研修用）</option>
```

### Backend 수정
**파일**: `backend/main.py`

```python
# 변경 전: 의도적으로 느린 구현
def slow_tfidf_search():
    # 5만 번 불필요한 루프
    for i in range(50000):
        temp_string = processed_query.upper().lower().strip()
    time.sleep(0.2)  # 200ms 지연
    
    # 10번 중복 벡터화
    for i in range(10):
        duplicate_vector = tfidf_vectorizer.transform([processed_query])
        time.sleep(0.05)  # 50ms 지연
    
    # 5번 유사도 재계산
    for i in range(5):
        temp_similarities = cosine_similarity(query_vector, tfidf_matrix)
        time.sleep(0.1)  # 100ms 지연

# 변경 후: 최적화된 구현
def slow_tfidf_search():
    # 모든 불필요한 지연 제거
    processed_query = preprocess_text(query)
    query_vector = tfidf_vectorizer.transform([processed_query])
    similarities = cosine_similarity(query_vector, tfidf_matrix)
```

## 결과

- 의도적인 성능 병목점 제거
- 모든 검색 방법 선택 가능
- 빠른 검색 성능 복원 
