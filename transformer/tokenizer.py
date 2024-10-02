import torch
import torch.nn as nn

# 1. 토큰화는 텍스트를 적절한 단위로 나누고 숫자 아이디로 변환하는 작업

# 띄어쓰기 단위로 분리
input_text = "나는 오늘 회사에 간다"
input_text_list = input_text.split()
print("input_text_list: ", input_text_list)

# 토큰 -> 아이디 딕셔너리와 아이디 -> 토큰 딕셔너리 만들기
str2idx = {word:idx for idx, word in enumerate(input_text_list)}
idx2str = {idx:word for idx, word in enumerate(input_text_list)}
print("str2idx: ", str2idx)
print("idx2str: ", idx2str)

# 토큰을 토큰 아이디로 변환
input_ids = [str2idx[word] for word in input_text_list]
print("input_ids: ", input_ids)


# 2. 토큰 임베딩으로 변환

# 딥러닝 모델이 텍스트 데이터를 처리하기 위해서는 입력으로 들어오는 토큰과 토큰 사이의 관계를 계산할 수 있어야한다.
# 1번에서 작성한 토큰 아이디는 하나의 숫자일 뿐이기 때문에 딥러닝 모델이 이를 처리할 수 없다. 의미를 담기위해서는 최소 2개 이상의 숫자 집합인 벡터로 볍환해야한다.
embedding_dim = 16
embed_layer = nn.Embedding(len(str2idx), embedding_dim)

input_embeddings = embed_layer(torch.tensor(input_ids))
input_embeddings = input_embeddings.unsqueeze(0)
input_embeddings.shape
torch.Size([1, 5, 16])

# 3. 위치 인코딩

# RNN과 트랜트포머의 가장 큰 차이점은 입력을 순차적으로 처리하는지 여부이다. 
# RNN은 순차적으로 처리하기 때문에 단어의 위치 정보를 알 수 있지만, 트랜스포머는 입력을 한번에 처리하기 때문에 단어의 위치 정보를 알 수 없다.
# 하지만 텍스트에서 순서는 중요한 정보이기 때문에 이를 위해 위치 인코딩을 사용한다.
embedding_dim = 16
max_position = 12
# 토큰 임베딩 층 생성
embed_layer = nn.Embedding(len(str2idx), embedding_dim)
# 위치 인코딩 층 생성
position_embed_layer = nn.Embedding(max_position, embedding_dim)

position_ids = torch.arange(len(input_ids), dtype=torch.long).unsqueeze(0)
position_encodings = position_embed_layer(position_ids)
token_embeddings = embed_layer(torch.tensor(input_ids)) # (5, 16)
token_embeddings = token_embeddings.unsqueeze(0) # (1, 5, 16)
# 토큰 임베딩과 위치 인코딩을 더해 최종 입력 임베딩 생성
input_embeddings = token_embeddings + position_encodings
input_embeddings.shape
torch.Size([1, 5, 16])

# 4. 어텐션
# 어텐션은 쿼리, 키, 밸류를 입력으로 받아 가중합을 계산하는 메커니즘. 어텐션은 셀프 어텐션과 멀티 헤드 어텐션으로 나뉨. 
# 셀프 어텐션은 쿼리, 키, 밸류가 모두 같은 경우를 말하며, 멀티 헤드 어텐션은 쿼리, 키, 밸류가 각각 다른 경우를 말함.

from math import sqrt
import torch.nn.functional as F

head_dim = 16

# 쿼리, 키, 값을 계산하기 위한 변환
weight_q = nn.Linear(embedding_dim, head_dim)
weight_k = nn.Linear(embedding_dim, head_dim)
weight_v = nn.Linear(embedding_dim, head_dim)
# 변환 수행
querys = weight_q(input_embeddings) # (1, 5, 16)
keys = weight_k(input_embeddings) # (1, 5, 16)
values = weight_v(input_embeddings) # (1, 5, 16)

def compute_attention(querys, keys, values, is_causal=False):
	dim_k = querys.size(-1) # 16
	scores = querys @ keys.transpose(-2, -1) / sqrt(dim_k)
	weights = F.softmax(scores, dim=-1)
	return weights @ values

print("원본 입력 형태: ", input_embeddings.shape)

after_attention_embeddings = compute_attention(querys, keys, values)

print("어텐션 적용 후 형태: ", after_attention_embeddings.shape)