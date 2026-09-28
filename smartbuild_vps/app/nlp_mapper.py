import streamlit as st
import torch
from sentence_transformers import SentenceTransformer, util
from stage_registry import GENERAL_STAGE, STRATEGY_DESCRIPTIONS

# 2. Кэшируем загрузку модели и векторизацию эталонов, чтобы Streamlit не тормозил
@st.cache_resource
def load_nlp_model():
    # Загружаем сверхлегкую модель
    model = SentenceTransformer('cointegrated/rubert-tiny2')
    
    # Подготавливаем ключи и векторы (эмбеддинги) наших эталонов
    corpus_keys = list(STRATEGY_DESCRIPTIONS.keys())
    corpus_embeddings = model.encode(list(STRATEGY_DESCRIPTIONS.values()), convert_to_tensor=True)
    
    return model, corpus_keys, corpus_embeddings

def predict_ai_strategy(task_name: str, threshold: float = 0.35) -> str:
    """
    Принимает строку (название работ из CSV) и возвращает наиболее подходящую ИИ-стратегию.
    """
    # Загружаем модель из кэша
    model, corpus_keys, corpus_embeddings = load_nlp_model()
    
    # Векторизуем название задачи из CSV
    task_emb = model.encode(task_name, convert_to_tensor=True)
    
    # Вычисляем косинусное сходство (cosine similarity)
    cos_scores = util.cos_sim(task_emb, corpus_embeddings)[0]
    
    # Находим индекс максимального совпадения
    best_idx = int(torch.argmax(cos_scores))
    best_score = float(cos_scores[best_idx])
    
    # Если сходство выше порога, возвращаем стратегию
    if best_score > threshold:
        return corpus_keys[best_idx]
    
    # Дефолтная стратегия, если ИИ не понял задачу
    return GENERAL_STAGE