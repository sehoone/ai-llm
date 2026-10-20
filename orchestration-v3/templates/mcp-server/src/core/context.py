from contextvars import ContextVar

# 현재 요청의 Correlation ID — RequestIDMiddleware가 설정, 로거가 읽음
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
