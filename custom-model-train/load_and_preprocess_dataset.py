from datasets import load_dataset
from transformers import AutoTokenizer
import torch

# 데이터셋 로드
dataset = load_dataset('json', data_files='custom-model-train/custom_dataset.json')

# 토크나이저 로드
model_id = 'distilbert-base-uncased-distilled-squad'
tokenizer = AutoTokenizer.from_pretrained(model_id)

# 데이터셋 전처리
def preprocess_function(examples):
    contexts = []
    questions = []
    answers = []
    for item in examples['data']:
        for entry in item:
            print("entry:", entry)
            paragraphs = entry['paragraphs']
            print("Paragraphs:", paragraphs)
            for paragraph in entry['paragraphs']:
                print(paragraph)
                context = paragraph['context']
                for qa in paragraph['qas']:
                    question = qa['question']
                    answer = qa['answers'][0]
                    contexts.append(context)
                    questions.append(question)
                    answers.append(answer)
    
    inputs = tokenizer(
        questions,
        contexts,
        max_length=384,
        truncation="only_second",
        return_offsets_mapping=True,
        padding="max_length",
        return_tensors="pt"
    )
    offset_mapping = inputs.pop("offset_mapping")
    start_positions = []
    end_positions = []

    for i, offset in enumerate(offset_mapping):
        answer = answers[i]
        start_char = answer["answer_start"]
        end_char = start_char + len(answer["text"])
        sequence_ids = inputs.sequence_ids(i)

        # Find the start and end of the context
        context_start = sequence_ids.index(1)
        context_end = len(sequence_ids) - 1 - sequence_ids[::-1].index(1)

        # If the answer is not fully inside the context, label it (0, 0)
        if not (offset[context_start][0] <= start_char and offset[context_end][1] >= end_char):
            start_positions.append(0)
            end_positions.append(0)
        else:
            # Otherwise move the start and end positions to the right location
            start_idx = torch.where((offset[:, 0] <= start_char) & (offset[:, 1] > start_char))[0]
            end_idx = torch.where((offset[:, 0] < end_char) & (offset[:, 1] >= end_char))[0]
            start_positions.append(start_idx.item() if len(start_idx) > 0 else 0)
            end_positions.append(end_idx.item() if len(end_idx) > 0 else 0)

    inputs["start_positions"] = start_positions
    inputs["end_positions"] = end_positions
    return inputs

# 데이터셋 전처리 적용
tokenized_datasets = dataset.map(lambda x: preprocess_function(x), batched=True)