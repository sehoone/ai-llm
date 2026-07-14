'use client'

import { useRef, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import {
  Trash2, Plus, Loader2, Upload, FileJson, FileText, File, Download,
  CheckCircle2, XCircle, Clock, Ban, ChevronLeft, ChevronRight,
} from 'lucide-react'
import { createEmbedding, deleteAllEmbeddings, deleteEmbedding, listEmbeddings, type DocumentItem } from '@/api/embeddings'
import { logger } from '@/lib/logger'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import {
  Form, FormControl, FormField, FormItem, FormLabel, FormMessage,
} from '@/components/ui/form'
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader,
  AlertDialogTitle, AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { Header } from '@/components/layout/header'
import { Main } from '@/components/layout/main'

// ── 타입 ────────────────────────────────────────────────────

type ItemStatus = 'pending' | 'processing' | 'success' | 'error' | 'cancelled'

interface ProgressItem {
  id: string | number
  title: string
  desc: string
  status: ItemStatus
  documentId?: number
  error?: string
}

// ── 샘플 파일 다운로드 ───────────────────────────────────────

const SAMPLE_DATA = [
  { id: 1, title: 'Python 기초 프로그래밍', desc: '과정 소개:\nPython 언어의 기본 문법과 프로그래밍 사고를 익히는 입문 과정입니다. 비개발자도 수강 가능하며 실습 중심으로 진행됩니다.\n\n학습 목표:\n- Python 설치 및 개발 환경 구성\n- 변수, 자료형, 조건문, 반복문 이해\n- 함수 정의 및 모듈 활용\n- 파일 입출력 및 예외 처리\n- 실전 미니 프로젝트 완성\n\n커리큘럼:\n1주차: 개발 환경 설정, 변수와 자료형\n2주차: 조건문, 반복문, 함수\n3주차: 리스트, 딕셔너리, 튜플\n4주차: 파일 처리, 모듈, 패키지\n5주차: 클래스와 객체지향 기초\n6주차: 미니 프로젝트 (데이터 처리 프로그램)\n\n수강 대상: 프로그래밍 경험이 없는 임직원 전원\n교육 기간: 6주 (주 2회, 회당 2시간)\n교육 형태: 집합교육 + 온라인 병행\n수강 정원: 20명\n선수 과목: 없음' },
  { id: 2, title: 'Python 데이터 분석 (pandas, numpy)', desc: '과정 소개:\n업무 데이터를 Python으로 분석하고 시각화하는 실무 중심 과정입니다. 엑셀 업무를 Python으로 대체하고 싶은 분께 적합합니다.\n\n학습 목표:\n- pandas를 활용한 데이터 로드, 정제, 변환\n- numpy를 활용한 수치 연산\n- matplotlib, seaborn으로 데이터 시각화\n- 실제 업무 데이터 분석 실습\n\n커리큘럼:\n1주차: pandas 기초 (DataFrame, Series)\n2주차: 데이터 필터링, 그룹핑, 집계\n3주차: 결측치 처리, 데이터 병합\n4주차: numpy 수치 연산\n5주차: matplotlib/seaborn 시각화\n6주차: 실무 데이터 분석 프로젝트\n\n수강 대상: Python 기초 과정 수료자 또는 Python 기본 문법 숙지자\n교육 기간: 6주 (주 2회, 회당 2시간)\n교육 형태: 집합교육\n수강 정원: 15명\n선수 과목: Python 기초 프로그래밍' },
  { id: 3, title: 'AWS 클라우드 입문', desc: '과정 소개:\nAmazon Web Services의 핵심 서비스를 이해하고 실습하는 입문 과정입니다. AWS SAA(Solutions Architect Associate) 자격증 취득을 위한 기초 단계입니다.\n\n학습 목표:\n- 클라우드 컴퓨팅 개념 및 AWS 글로벌 인프라 이해\n- EC2, S3, RDS, VPC 핵심 서비스 실습\n- IAM을 활용한 권한 관리\n- 비용 관리 및 최적화 방법\n\n커리큘럼:\n1주차: 클라우드 개념, AWS 계정 설정, IAM\n2주차: EC2 인스턴스 생성 및 관리\n3주차: S3 스토리지 활용\n4주차: VPC 네트워크 구성\n5주차: RDS 데이터베이스 운영\n6주차: 아키텍처 설계 실습\n\n수강 대상: 인프라/개발 직무 임직원, 클라우드 전환 업무 담당자\n교육 기간: 6주 (주 2회, 회당 2시간)\n교육 형태: 온라인 실습 환경 제공\n수강 정원: 20명\n선수 과목: 기본 리눅스 명령어 이해 권장' },
  { id: 4, title: 'AWS Solutions Architect Associate 자격증 대비', desc: '과정 소개:\nAWS SAA-C03 자격증 취득을 목표로 하는 심화 과정입니다. 시험 출제 범위를 체계적으로 학습하고 모의고사를 통해 실전 대비합니다.\n\n학습 목표:\n- AWS Well-Architected Framework 이해\n- 고가용성, 확장성, 재해복구 아키텍처 설계\n- 보안 및 비용 최적화 전략\n- SAA-C03 시험 합격\n\n커리큘럼:\n1~2주차: 컴퓨팅 서비스 (EC2, Lambda, ECS)\n3~4주차: 스토리지 (S3, EBS, EFS, Glacier)\n5~6주차: 데이터베이스 (RDS, DynamoDB, ElastiCache)\n7~8주차: 네트워킹 (VPC, CloudFront, Route53)\n9~10주차: 보안 및 모니터링\n11~12주차: 모의고사 및 오답노트\n\n수강 대상: AWS 입문 과정 수료자 또는 AWS 기본 지식 보유자\n교육 기간: 12주 (주 2회, 회당 2시간)\n교육 형태: 온라인 + 집합교육 병행\n수강 정원: 15명\n자격증 응시료: 회사 전액 지원' },
  { id: 5, title: 'Docker & Kubernetes 실무', desc: '과정 소개:\n컨테이너 기술의 핵심인 Docker와 Kubernetes를 실무에 적용하는 과정입니다. CI/CD 파이프라인 구축까지 다룹니다.\n\n학습 목표:\n- Docker 이미지 빌드 및 컨테이너 운영\n- Docker Compose를 활용한 멀티 컨테이너 관리\n- Kubernetes 클러스터 구성 및 운영\n- Helm Chart를 활용한 애플리케이션 배포\n- GitHub Actions 기반 CI/CD 파이프라인 구축\n\n커리큘럼:\n1주차: Docker 기초, Dockerfile 작성\n2주차: Docker Compose, 네트워크/볼륨\n3주차: Kubernetes 아키텍처, Pod/Deployment\n4주차: Service, ConfigMap, Secret\n5주차: Ingress, HPA, 스토리지\n6주차: Helm, CI/CD 파이프라인 구축\n\n수강 대상: 개발/인프라 직무, 리눅스 기본 명령어 사용 가능자\n교육 기간: 6주 (주 2회, 회당 2시간)\n교육 형태: 실습 환경 제공 (클러스터 1인 1개)\n수강 정원: 12명' },
  { id: 6, title: 'LLM 활용 및 프롬프트 엔지니어링', desc: '과정 소개:\nChatGPT, Claude 등 대형 언어 모델(LLM)을 업무에 효과적으로 활용하고, 프롬프트 엔지니어링 기법을 습득하는 과정입니다.\n\n학습 목표:\n- LLM의 동작 원리 이해\n- 효과적인 프롬프트 작성 기법 (Zero-shot, Few-shot, Chain-of-Thought)\n- API를 활용한 LLM 업무 자동화\n- RAG(검색 증강 생성) 기초 이해\n- 업무별 프롬프트 템플릿 작성\n\n커리큘럼:\n1주차: LLM 개요, ChatGPT/Claude 기초 활용\n2주차: 프롬프트 설계 원칙 및 기법\n3주차: 문서 작성, 코드 생성, 데이터 분석 활용\n4주차: OpenAI API 기초 실습\n5주차: RAG 개념 및 간단한 구현\n6주차: 부서별 업무 자동화 프로젝트\n\n수강 대상: 전 직원 (직무 무관)\n교육 기간: 6주 (주 1회, 회당 2시간)\n교육 형태: 온라인 + 실습\n수강 정원: 30명' },
  { id: 7, title: 'Spring Boot 백엔드 개발', desc: '과정 소개:\nJava 기반 Spring Boot 프레임워크를 활용하여 RESTful API 서버를 개발하는 실무 과정입니다.\n\n학습 목표:\n- Spring Boot 프로젝트 구조 이해\n- JPA/Hibernate를 활용한 데이터베이스 연동\n- RESTful API 설계 및 구현\n- Spring Security를 활용한 인증/인가\n- 테스트 코드 작성 (JUnit5, Mockito)\n\n커리큘럼:\n1주차: Spring Boot 기초, 프로젝트 구조\n2주차: REST API 개발 (Controller, Service, Repository)\n3주차: JPA/Hibernate, 데이터베이스 연동\n4주차: Spring Security, JWT 인증\n5주차: 테스트 코드 작성\n6주차: 배포 (Docker, AWS EC2)\n\n수강 대상: Java 기본 문법 숙지자, 백엔드 개발 희망자\n교육 기간: 8주 (주 2회, 회당 2시간)\n교육 형태: 집합교육 + 코드 리뷰\n수강 정원: 10명\n선수 과목: Java 기초 또는 동등 수준' },
  { id: 8, title: 'React 프론트엔드 개발', desc: '과정 소개:\nReact를 활용하여 현대적인 웹 프론트엔드를 개발하는 실무 과정입니다. TypeScript와 함께 실제 프로젝트를 완성합니다.\n\n학습 목표:\n- React 컴포넌트 설계 및 개발\n- TypeScript를 활용한 타입 안전 코드 작성\n- React Hook 활용 (useState, useEffect, useContext)\n- 상태 관리 (Zustand 또는 Redux Toolkit)\n- REST API 연동 및 비동기 처리\n\n커리큘럼:\n1주차: React 기초, JSX, 컴포넌트\n2주차: Props, State, 이벤트 처리\n3주차: TypeScript 기초 + React 적용\n4주차: React Hook 심화\n5주차: 상태 관리, API 연동\n6주차: 라우팅, 성능 최적화\n7~8주차: 미니 프로젝트 (CRUD 애플리케이션)\n\n수강 대상: HTML/CSS/JavaScript 기본 지식 보유자\n교육 기간: 8주 (주 2회, 회당 2시간)\n교육 형태: 집합교육\n수강 정원: 10명' },
  { id: 9, title: '데이터베이스 설계 및 SQL 심화', desc: '과정 소개:\n관계형 데이터베이스 설계 원칙과 PostgreSQL/MySQL 기반 고급 SQL을 학습하는 과정입니다.\n\n학습 목표:\n- ERD 설계 및 정규화 (1NF~3NF)\n- 복잡한 JOIN, 서브쿼리, CTE 활용\n- 인덱스 설계 및 쿼리 최적화\n- 트랜잭션 및 동시성 제어\n- 실행 계획(EXPLAIN) 분석\n\n커리큘럼:\n1주차: 관계형 모델, ERD 설계\n2주차: 정규화, 테이블 설계 실습\n3주차: JOIN 심화, 서브쿼리, CTE\n4주차: 윈도우 함수, 집계 함수\n5주차: 인덱스 설계, 쿼리 최적화\n6주차: 트랜잭션, 잠금, 동시성\n\n수강 대상: SQL 기본 SELECT 문 사용 가능한 개발/분석 직무 임직원\n교육 기간: 6주 (주 2회, 회당 2시간)\n교육 형태: 실습 DB 환경 제공\n수강 정원: 15명' },
  { id: 10, title: '정보보안 기초 및 개인정보보호', desc: '과정 소개:\n임직원 모두가 알아야 할 정보보안 기본 수칙과 개인정보 보호법 준수 사항을 학습하는 필수 과정입니다. 연 1회 이수 의무입니다.\n\n학습 목표:\n- 정보보안 위협 유형 이해 (피싱, 랜섬웨어, 사회공학)\n- 안전한 비밀번호 관리 및 PC 보안\n- 개인정보 수집·처리·파기 원칙\n- 개인정보보호법 주요 조항 이해\n- 보안 사고 발생 시 대응 절차\n\n커리큘럼:\n1강 (1시간): 최신 보안 위협 동향\n2강 (1시간): 임직원 보안 수칙\n3강 (1시간): 개인정보보호법 개요\n4강 (1시간): 개인정보 처리 실무\n5강 (30분): 모의 피싱 대응 훈련\n6강 (30분): 평가 및 수료\n\n수강 대상: 전 임직원 (필수 이수)\n교육 기간: 1일 (총 5시간)\n교육 형태: 온라인 자기학습\n이수 기준: 80점 이상 (재응시 가능)\n이수 마감: 매년 12월 31일' },
  { id: 11, title: '신입사원 직무 기초 교육', desc: '과정 소개:\n입사 후 3개월 이내 필수 이수 과정으로, 회사 문화, 조직 이해, 기본 업무 역량을 키웁니다.\n\n학습 목표:\n- 회사 비전, 미션, 핵심 가치 이해\n- 조직 구조 및 주요 부서 역할 파악\n- 업무 보고 및 문서 작성 방법\n- 회의 진행 및 참여 에티켓\n- 사내 시스템 활용 (인트라넷, 메신저, 협업도구)\n\n커리큘럼:\n1일차: 회사 소개, 경영 전략, 조직 문화\n2일차: 조직도 이해, 부서별 업무 소개\n3일차: 비즈니스 커뮤니케이션 (이메일, 보고서)\n4일차: 회의 스킬, 발표 기법\n5일차: 사내 시스템 실습, Q&A\n\n수강 대상: 입사 후 3개월 이내 신입사원 전원\n교육 기간: 5일 (집중 합숙)\n교육 형태: 집합교육 + 선배 멘토 매칭\n수강 정원: 기수별 30명\n이수 필수 여부: 필수' },
  { id: 12, title: '리더십 역량 개발 (팀장급)', desc: '과정 소개:\n팀장 및 리더 직급을 위한 리더십 역량 강화 과정입니다. 팀 성과 관리, 구성원 코칭, 의사결정 능력을 향상시킵니다.\n\n학습 목표:\n- 상황별 리더십 스타일 적용\n- 성과 목표 설정 (OKR/KPI)\n- 1:1 코칭 및 피드백 스킬\n- 갈등 관리 및 중재 기법\n- 변화 관리 및 조직 동기 부여\n\n커리큘럼:\n1일차: 리더십 자기 진단, 현대 리더십 트렌드\n2일차: OKR 설정 및 성과 관리\n3일차: 코칭 스킬 실습 (Role Play)\n4일차: 갈등 해결, 어려운 대화 다루기\n5일차: 변화 관리, 종합 액션 플랜 작성\n\n수강 대상: 팀장, 파트장 및 리더 직급 임직원\n교육 기간: 5일 (연속 또는 분산 진행)\n교육 형태: 집합교육 + 외부 강사\n수강 정원: 20명\n개설 주기: 반기 1회' },
  { id: 13, title: '비즈니스 영어 커뮤니케이션', desc: '과정 소개:\n글로벌 업무 환경에서 필요한 비즈니스 영어 능력을 향상시키는 과정입니다. 이메일 작성, 회의 참여, 프레젠테이션에 초점을 맞춥니다.\n\n학습 목표:\n- 비즈니스 이메일 작성 (요청, 제안, 거절)\n- 화상 회의 영어 표현\n- 영문 보고서 및 제안서 작성\n- 프레젠테이션 영어 스크립트 구성\n- 협상 및 미팅 영어\n\n커리큘럼:\n1~3주차: 비즈니스 이메일 유형별 작성\n4~5주차: 회의 진행 영어 표현\n6~7주차: 프레젠테이션 구성 및 발표\n8~9주차: 보고서, 제안서 작성\n10~12주차: 협상 시뮬레이션, 최종 발표\n\n수강 대상: 영어 업무 필요 임직원 (TOEIC 700점 이상 권장)\n교육 기간: 12주 (주 2회, 회당 1.5시간)\n교육 형태: 소그룹 (4~6명) 회화 수업\n수강 정원: 6명\n강사: 원어민 + 한국인 강사 공동 진행' },
  { id: 14, title: '프로젝트 관리 (PMP 기반)', desc: '과정 소개:\nPMBOK 가이드를 기반으로 프로젝트 관리 전 생애주기를 학습하고 PMP 자격증 취득을 준비하는 과정입니다.\n\n학습 목표:\n- 프로젝트 관리 5대 프로세스 그룹 이해\n- 10대 지식 영역 (범위, 일정, 비용, 품질 등)\n- WBS, 간트 차트, 리스크 관리 계획 수립\n- 애자일/스크럼 방법론 이해\n- PMP 시험 대비 (모의고사)\n\n커리큘럼:\n1~2주차: 프로젝트 관리 개요, 착수 프로세스\n3~4주차: 범위 관리, WBS 작성\n5~6주차: 일정 관리, 크리티컬 패스\n7~8주차: 비용, 품질, 리스크 관리\n9~10주차: 의사소통, 조달, 이해관계자 관리\n11~12주차: 애자일 방법론, 모의고사\n\n수강 대상: PM, PL 직무 또는 프로젝트 관리 업무 담당자\n교육 기간: 12주 (주 2회, 회당 2시간)\n교육 형태: 집합교육\n수강 정원: 15명\n자격증 응시료: 회사 전액 지원' },
  { id: 15, title: '커뮤니케이션 스킬 향상', desc: '과정 소개:\n직장 내 효과적인 커뮤니케이션 방법을 학습하고 실습하는 과정입니다. 보고, 설득, 피드백, 갈등 해결을 다룹니다.\n\n학습 목표:\n- 상황별 커뮤니케이션 전략 이해\n- 피라미드 구조 기반 논리적 보고\n- 비폭력 대화(NVC) 기법 적용\n- 효과적인 피드백 주고받기\n- 어려운 상황에서의 대화 기술\n\n커리큘럼:\n1일차: 커뮤니케이션 진단, 경청 스킬\n2일차: 논리적 보고 기술 (PREP, STAR 기법)\n3일차: 설득과 협상 커뮤니케이션\n4일차: 갈등 상황 대화법, 피드백 기술\n5일차: 롤플레이 실습, 개인 개선 계획 수립\n\n수강 대상: 전 임직원 (특히 대리~과장급 권장)\n교육 기간: 5일 (집중)\n교육 형태: 집합교육 + 실습\n수강 정원: 20명\n개설 주기: 분기 1회' },
  { id: 16, title: '데이터 기반 의사결정', desc: '과정 소개:\n데이터를 활용하여 업무 의사결정의 질을 높이는 방법을 학습합니다. 비개발자도 데이터를 읽고 분석하는 능력을 기릅니다.\n\n학습 목표:\n- 데이터 리터러시 개념 이해\n- 핵심 지표(KPI) 설정 및 측정 방법\n- Excel/Google Sheets 고급 분석 기능\n- 데이터 시각화 원칙 (어떤 차트를 언제 쓸까)\n- A/B 테스트 설계 기초\n- 대시보드 구성 및 해석\n\n커리큘럼:\n1주차: 데이터 리터러시, KPI 설계\n2주차: Excel 피벗테이블, 고급 함수\n3주차: 데이터 시각화 원칙\n4주차: Google Looker Studio 대시보드 실습\n5주차: A/B 테스트 개념 및 사례\n6주차: 데이터 기반 의사결정 케이스 스터디\n\n수강 대상: 기획, 마케팅, 운영 직무 임직원\n교육 기간: 6주 (주 1회, 회당 2시간)\n교육 형태: 온라인 + 실습\n수강 정원: 25명' },
  { id: 17, title: '애자일/스크럼 실무 적용', desc: '과정 소개:\n스크럼 프레임워크를 팀에 실제로 적용하기 위한 실무 과정입니다. 스크럼 마스터 역할을 포함한 애자일 전환을 지원합니다.\n\n학습 목표:\n- 애자일 선언 및 12개 원칙 이해\n- 스크럼 3가지 역할 (PO, SM, 개발팀)\n- 스프린트 계획, 데일리 스크럼, 회고 진행\n- 제품 백로그 및 스프린트 백로그 작성\n- Jira를 활용한 스크럼 보드 운영\n\n커리큘럼:\n1일차: 애자일 개요, 스크럼 프레임워크\n2일차: 역할과 의례(Ceremony) 실습\n3일차: 백로그 작성, 스토리 포인트 추정\n4일차: 스프린트 시뮬레이션\n5일차: 회고 퍼실리테이션, 팀 적용 계획\n\n수강 대상: 개발/기획/디자인 직무 및 스크럼 마스터 희망자\n교육 기간: 5일\n교육 형태: 집합교육 + 시뮬레이션\n수강 정원: 16명\n관련 자격증: PSM I (Professional Scrum Master) 취득 지원' },
  { id: 18, title: '직장 내 성희롱 예방 교육', desc: '과정 소개:\n직장 내 성희롱 예방 및 대응 방법을 학습하는 법정 의무 교육입니다. 매년 1회 전 임직원이 이수해야 합니다.\n\n학습 목표:\n- 직장 내 성희롱의 정의 및 유형 이해\n- 성희롱 발생 시 피해자 지원 절차\n- 신고 방법 및 2차 피해 방지\n- 올바른 직장 문화 형성 방법\n\n커리큘럼:\n1강 (30분): 성희롱 개념 및 판단 기준\n2강 (30분): 직장 내 사례 분석\n3강 (30분): 피해자 지원 및 신고 절차\n4강 (30분): 건강한 조직 문화\n\n수강 대상: 전 임직원 (필수 이수)\n교육 시간: 총 2시간\n교육 형태: 온라인 자기학습\n이수 기준: 전 강의 완료 + 확인 서명\n이수 마감: 매년 9월 30일\n미이수 시: 인사 불이익 발생 가능' },
  { id: 19, title: 'Excel 업무 활용 고급', desc: '과정 소개:\n엑셀을 업무에서 더 효율적으로 사용하기 위한 고급 기능을 학습합니다. 반복 업무 자동화와 데이터 분석에 집중합니다.\n\n학습 목표:\n- VLOOKUP, INDEX/MATCH, XLOOKUP 마스터\n- 피벗 테이블 고급 활용\n- 조건부 서식 자동화\n- 매크로 및 VBA 기초\n- 파워 쿼리를 활용한 데이터 변환\n\n커리큘럼:\n1주차: 고급 함수 (VLOOKUP, INDEX/MATCH, 배열 수식)\n2주차: 피벗 테이블 고급, 피벗 차트\n3주차: 조건부 서식, 데이터 유효성 검사\n4주차: 매크로 기록 및 VBA 기초\n5주차: 파워 쿼리 데이터 연결 및 변환\n6주차: 업무 자동화 프로젝트\n\n수강 대상: Excel 기본 사용 가능자, 사무 직군 전반\n교육 기간: 6주 (주 1회, 회당 2시간)\n교육 형태: 집합교육 (컴퓨터 실습실)\n수강 정원: 20명' },
  { id: 20, title: '디자인 씽킹 (Design Thinking)', desc: '과정 소개:\n사용자 중심의 문제 해결 방법론인 디자인 씽킹을 습득하여 혁신적인 아이디어를 도출하고 실행하는 과정입니다.\n\n학습 목표:\n- 디자인 씽킹 5단계 프로세스 이해 (공감-정의-아이디에이션-프로토타이핑-테스트)\n- 사용자 인터뷰 및 공감 맵 작성\n- HMW(How Might We) 질문법\n- 아이디어 도출 및 우선순위화\n- 빠른 프로토타이핑 기법\n\n커리큘럼:\n1일차: 디자인 씽킹 개요, 사례 연구\n2일차: 공감 단계 - 사용자 인터뷰 실습\n3일차: 정의 단계 - POV, HMW 작성\n4일차: 아이디에이션 - 브레인스토밍, 아이디어 선정\n5일차: 프로토타이핑 및 테스트 실습\n\n수강 대상: 기획, 서비스, UX 직무 및 혁신 활동 참여자\n교육 기간: 5일 (연속 진행)\n교육 형태: 팀 프로젝트 중심 워크숍\n수강 정원: 20명 (4명 × 5팀)' },
  { id: 21, title: 'Git & GitHub 버전 관리 실무', desc: '과정 소개:\nGit 버전 관리 시스템과 GitHub을 활용하여 팀 협업 개발 워크플로우를 구축하고 운영하는 과정입니다.\n\n학습 목표:\n- Git 기본 명령어 완전 이해\n- 브랜치 전략 (Git Flow, GitHub Flow)\n- Pull Request 및 코드 리뷰 문화\n- 충돌 해결 및 rebase 활용\n- GitHub Actions를 활용한 CI/CD 기초\n\n커리큘럼:\n1주차: Git 기초 (init, add, commit, push, pull)\n2주차: 브랜치 생성, 병합, 충돌 해결\n3주차: GitHub Flow, Pull Request 실습\n4주차: rebase, cherry-pick, stash\n5주차: GitHub Actions CI/CD 파이프라인\n6주차: 팀 프로젝트 협업 실습\n\n수강 대상: 개발 직군 전원 (신입 포함)\n교육 기간: 6주 (주 1회, 회당 2시간)\n교육 형태: 실습 중심\n수강 정원: 15명\n선수 과목: 기본 터미널/명령어 사용 가능자' },
]

const SAMPLE_JSON = JSON.stringify(SAMPLE_DATA, null, 2)

function csvEscape(s: string | number) { return `"${String(s).replace(/"/g, '""')}"` }
const SAMPLE_CSV = [
  'id,title,desc',
  ...SAMPLE_DATA.map(r => `${r.id},${csvEscape(r.title)},${csvEscape(r.desc)}`),
].join('\n')

function downloadFile(content: string, filename: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType })
  const url  = URL.createObjectURL(blob)
  const a    = document.createElement('a')
  a.href     = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

// ── CSV 파서 ────────────────────────────────────────────────

function parseCsvLine(line: string): string[] {
  const result: string[] = []
  let current = ''
  let inQuotes = false
  for (let i = 0; i < line.length; i++) {
    const ch = line[i]
    if (ch === '"') {
      if (inQuotes && line[i + 1] === '"') { current += '"'; i++ }
      else { inQuotes = !inQuotes }
    } else if (ch === ',' && !inQuotes) {
      result.push(current); current = ''
    } else {
      current += ch
    }
  }
  result.push(current)
  return result
}

function parseCsv(text: string): Array<{ id: string | number; title: string; desc: string }> {
  const lines = text.trim().split(/\r?\n/).filter(l => l.trim())
  if (lines.length < 2) throw new Error('CSV에 데이터 행이 없습니다.')
  const headers = parseCsvLine(lines[0]).map(h => h.trim().toLowerCase().replace(/^"|"$/g, ''))
  const idIdx    = headers.indexOf('id')
  const titleIdx = headers.indexOf('title')
  const descIdx  = headers.indexOf('desc')
  if (idIdx === -1 || titleIdx === -1 || descIdx === -1) {
    throw new Error('CSV 헤더에 id, title, desc 컬럼이 필요합니다.')
  }
  return lines.slice(1).map(line => {
    const cols = parseCsvLine(line)
    return {
      id:    cols[idIdx]?.trim()    ?? '',
      title: cols[titleIdx]?.trim() ?? '',
      desc:  cols[descIdx]?.trim()  ?? '',
    }
  })
}

// ── 스키마 ──────────────────────────────────────────────────

const singleSchema = z.object({
  title: z.string().min(1, '제목을 입력하세요').max(500),
  content: z.string().min(1, '내용을 입력하세요'),
})
type SingleValues = z.infer<typeof singleSchema>

const jsonItemSchema = z.object({
  id: z.union([z.string(), z.number()]),
  title: z.string().min(1),
  desc: z.string().min(1),
})
const jsonFileSchema = z.array(jsonItemSchema).min(1, '항목이 1건 이상이어야 합니다.')

// ── 상태 아이콘 ──────────────────────────────────────────────

function StatusIcon({ status }: { status: ItemStatus }) {
  if (status === 'pending')    return <Clock     className='h-4 w-4 text-muted-foreground' />
  if (status === 'processing') return <Loader2   className='h-4 w-4 animate-spin text-blue-500' />
  if (status === 'success')    return <CheckCircle2 className='h-4 w-4 text-green-500' />
  if (status === 'error')      return <XCircle   className='h-4 w-4 text-destructive' />
  if (status === 'cancelled')  return <Ban       className='h-4 w-4 text-muted-foreground' />
  return null
}

function rowBg(status: ItemStatus) {
  if (status === 'processing') return 'bg-blue-50 dark:bg-blue-950/20'
  if (status === 'success')    return 'bg-green-50 dark:bg-green-950/20'
  if (status === 'error')      return 'bg-red-50 dark:bg-red-950/20'
  return ''
}

// ── 페이지 번호 배열 생성 (1, ..., n-1, n, n+1, ..., last) ──

function getPageNumbers(current: number, total: number): (number | 'ellipsis')[] {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i)
  const pages: (number | 'ellipsis')[] = [0]
  const left  = Math.max(1, current - 1)
  const right = Math.min(total - 2, current + 1)
  if (left > 1)         pages.push('ellipsis')
  for (let i = left; i <= right; i++) pages.push(i)
  if (right < total - 2) pages.push('ellipsis')
  pages.push(total - 1)
  return pages
}

// ── 메인 컴포넌트 ────────────────────────────────────────────

const PAGE_SIZE = 10

export function EmbeddingsFeature() {
  const queryClient = useQueryClient()
  const [deletingId, setDeletingId] = useState<number | null>(null)
  const [selectedDoc, setSelectedDoc] = useState<DocumentItem | null>(null)
  const [docDialogOpen, setDocDialogOpen] = useState(false)
  const [page, setPage] = useState(0)

  // 단건 폼
  const form = useForm<SingleValues>({
    resolver: zodResolver(singleSchema),
    defaultValues: { title: '', content: '' },
  })

  // 다건 업로드 상태
  const fileInputRef  = useRef<HTMLInputElement>(null)
  const cancelledRef  = useRef(false)
  const [fileName,       setFileName]       = useState<string | null>(null)
  const [fileType,       setFileType]       = useState<'json' | 'csv' | null>(null)
  const [parseError,     setParseError]     = useState<string | null>(null)
  const [parsedItems,    setParsedItems]    = useState<z.infer<typeof jsonItemSchema>[] | null>(null)
  const [progressItems,  setProgressItems]  = useState<ProgressItem[]>([])
  const [isUploading,    setIsUploading]    = useState(false)

  // ── 쿼리 / 뮤테이션 ─────────────────────────────────────

  const { data: pagedData, isLoading } = useQuery({
    queryKey: ['embeddings', page],
    queryFn: () => listEmbeddings(page, PAGE_SIZE),
  })

  const documents = pagedData?.content ?? []
  const totalElements = pagedData?.totalElements ?? 0
  const totalPages = pagedData?.totalPages ?? 0

  const createMutation = useMutation({
    mutationFn: createEmbedding,
    onSuccess: (data) => {
      toast.success(`"${data.title}" 임베딩이 생성되었습니다.`)
      form.reset()
      setPage(0)
      queryClient.invalidateQueries({ queryKey: ['embeddings'] })
    },
    onError: (err) => {
      logger.error('임베딩 생성 실패', err)
      toast.error('임베딩 생성에 실패했습니다.')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: deleteEmbedding,
    onSuccess: () => {
      toast.success('문서가 삭제되었습니다.')
      queryClient.invalidateQueries({ queryKey: ['embeddings'] })
    },
    onError: (err) => {
      logger.error('문서 삭제 실패', err)
      toast.error('삭제에 실패했습니다.')
    },
    onSettled: () => setDeletingId(null),
  })

  const deleteAllMutation = useMutation({
    mutationFn: deleteAllEmbeddings,
    onSuccess: () => {
      toast.success('전체 문서가 삭제되었습니다.')
      setPage(0)
      queryClient.invalidateQueries({ queryKey: ['embeddings'] })
    },
    onError: (err) => {
      logger.error('전체 삭제 실패', err)
      toast.error('전체 삭제에 실패했습니다.')
    },
  })

  // ── 핸들러 ──────────────────────────────────────────────

  const onSingleSubmit = (values: SingleValues) => createMutation.mutate(values)

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setFileName(file.name)
    setParsedItems(null)
    setParseError(null)
    setProgressItems([])

    const isCsv = file.name.toLowerCase().endsWith('.csv')
    setFileType(isCsv ? 'csv' : 'json')

    const reader = new FileReader()
    reader.onload = (ev) => {
      try {
        const text = ev.target?.result as string
        const raw  = isCsv ? parseCsv(text) : JSON.parse(text)
        const parsed = jsonFileSchema.parse(raw)
        setParsedItems(parsed)
      } catch (err) {
        if (err instanceof z.ZodError) {
          setParseError(`형식 오류: ${err.issues[0]?.message ?? '알 수 없는 오류'}`)
        } else if (err instanceof Error) {
          setParseError(err.message)
        } else {
          setParseError('파일 파싱 실패. 올바른 형식인지 확인하세요.')
        }
      }
    }
    reader.readAsText(file)
    e.target.value = ''
  }

  const startUpload = async () => {
    if (!parsedItems || parsedItems.length === 0) return

    // 진행 목록 초기화 (모두 pending)
    const initial: ProgressItem[] = parsedItems.map(item => ({ ...item, status: 'pending' }))
    setProgressItems(initial)
    cancelledRef.current = false
    setIsUploading(true)

    let successCount = 0
    let errorCount   = 0

    for (let i = 0; i < initial.length; i++) {
      // 취소 확인
      if (cancelledRef.current) {
        setProgressItems(prev =>
          prev.map((p, idx) => idx >= i ? { ...p, status: 'cancelled' } : p)
        )
        break
      }

      // 처리 중 표시
      setProgressItems(prev =>
        prev.map((p, idx) => idx === i ? { ...p, status: 'processing' } : p)
      )

      try {
        const result = await createEmbedding({ title: initial[i].title, content: initial[i].desc })
        setProgressItems(prev =>
          prev.map((p, idx) =>
            idx === i ? { ...p, status: 'success', documentId: result.id } : p
          )
        )
        successCount++
      } catch (err) {
        const message = err instanceof Error ? err.message : '알 수 없는 오류'
        logger.error('다건 업로드 개별 실패', { id: initial[i].id, message })
        setProgressItems(prev =>
          prev.map((p, idx) => idx === i ? { ...p, status: 'error', error: message } : p)
        )
        errorCount++
      }
    }

    setIsUploading(false)
    queryClient.invalidateQueries({ queryKey: ['embeddings'] })

    if (cancelledRef.current) {
      toast.warning(`업로드가 취소되었습니다. (완료 ${successCount}건)`)
    } else if (errorCount === 0) {
      toast.success(`${successCount}건 모두 업로드 완료되었습니다.`)
    } else {
      toast.warning(`${successCount}건 성공, ${errorCount}건 실패했습니다.`)
    }
  }

  const cancelUpload = () => { cancelledRef.current = true }

  const resetBulk = () => {
    setParsedItems(null)
    setProgressItems([])
    setParseError(null)
    setFileName(null)
    setFileType(null)
    cancelledRef.current = false
  }

  // ── 진행 통계 (파생값) ──────────────────────────────────

  const doneCount    = progressItems.filter(p => p.status === 'success' || p.status === 'error').length
  const successCount = progressItems.filter(p => p.status === 'success').length
  const errorCount   = progressItems.filter(p => p.status === 'error').length
  const totalCount   = progressItems.length
  const progressPct  = totalCount > 0 ? Math.round((doneCount / totalCount) * 100) : 0

  const isStarted  = progressItems.length > 0
  const isFinished = isStarted && !isUploading

  // ── 렌더 ────────────────────────────────────────────────

  return (
    <>
      <Header>
        <h1 className='text-lg font-semibold'>임베딩 관리</h1>
      </Header>
      <Main>
        <div className='space-y-6'>

          {/* 임베딩 생성 */}
          <Card>
            <CardHeader>
              <CardTitle className='text-base'>임베딩 생성</CardTitle>
            </CardHeader>
            <CardContent>
              <Tabs defaultValue='single'>
                <TabsList className='mb-4'>
                  <TabsTrigger value='single'>단건 입력</TabsTrigger>
                  <TabsTrigger value='bulk'>파일 업로드 (JSON / CSV)</TabsTrigger>
                </TabsList>

                {/* ── 단건 입력 ── */}
                <TabsContent value='single'>
                  <Form {...form}>
                    <form onSubmit={form.handleSubmit(onSingleSubmit)} className='space-y-4'>
                      <FormField
                        control={form.control}
                        name='title'
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>제목</FormLabel>
                            <FormControl>
                              <Input placeholder='문서 제목을 입력하세요' {...field} />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                      <FormField
                        control={form.control}
                        name='content'
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>내용</FormLabel>
                            <FormControl>
                              <Textarea
                                placeholder='임베딩할 텍스트 내용을 입력하세요'
                                className='min-h-[120px] resize-none'
                                {...field}
                              />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                      <Button type='submit' disabled={createMutation.isPending}>
                        {createMutation.isPending
                          ? <><Loader2 className='mr-2 h-4 w-4 animate-spin' />임베딩 생성 중...</>
                          : <><Plus    className='mr-2 h-4 w-4' />임베딩 생성</>}
                      </Button>
                    </form>
                  </Form>
                </TabsContent>

                {/* ── JSON 파일 업로드 ── */}
                <TabsContent value='bulk'>
                  <div className='space-y-4'>

                    {/* 포맷 안내 + 샘플 다운로드 */}
                    <div className='space-y-2 rounded-md bg-muted px-4 py-3 text-xs text-muted-foreground'>
                      <div className='flex items-start justify-between gap-4'>
                        <div className='flex-1 space-y-2'>
                          <div>
                            <p className='mb-1 font-medium'>JSON 파일 형식</p>
                            <pre className='font-mono'>{`[\n  { "id": 1, "title": "제목", "desc": "내용" },\n  ...\n]`}</pre>
                          </div>
                          <div>
                            <p className='mb-1 font-medium'>CSV 파일 형식</p>
                            <pre className='font-mono'>{`id,title,desc\n1,제목,내용\n2,제목2,"쉼표 포함 시 따옴표로 감쌈"`}</pre>
                          </div>
                        </div>
                        <div className='flex shrink-0 flex-col gap-1.5 pt-0.5'>
                          <Button
                            variant='outline'
                            size='sm'
                            className='h-7 gap-1.5 text-xs'
                            onClick={() => downloadFile(SAMPLE_JSON, 'sample.json', 'application/json')}
                          >
                            <Download className='h-3 w-3' />
                            JSON 샘플
                          </Button>
                          <Button
                            variant='outline'
                            size='sm'
                            className='h-7 gap-1.5 text-xs'
                            onClick={() => downloadFile(SAMPLE_CSV, 'sample.csv', 'text/csv')}
                          >
                            <Download className='h-3 w-3' />
                            CSV 샘플
                          </Button>
                        </div>
                      </div>
                    </div>

                    {/* 파일 선택 */}
                    <div className='flex items-center gap-3'>
                      <input
                        ref={fileInputRef}
                        type='file'
                        accept='.json,application/json,.csv,text/csv'
                        className='hidden'
                        onChange={onFileChange}
                        disabled={isUploading}
                      />
                      <Button
                        variant='outline'
                        onClick={() => fileInputRef.current?.click()}
                        disabled={isUploading}
                      >
                        {fileType === 'csv'
                          ? <FileText className='mr-2 h-4 w-4' />
                          : fileType === 'json'
                            ? <FileJson className='mr-2 h-4 w-4' />
                            : <File className='mr-2 h-4 w-4' />}
                        파일 선택 (JSON / CSV)
                      </Button>
                      {fileName && (
                        <span className='flex items-center gap-1 text-sm text-muted-foreground'>
                          {fileType === 'csv'
                            ? <FileText className='h-3.5 w-3.5' />
                            : <FileJson className='h-3.5 w-3.5' />}
                          {fileName}
                        </span>
                      )}
                    </div>

                    {/* 파싱 오류 */}
                    {parseError && (
                      <p className='text-sm text-destructive'>{parseError}</p>
                    )}

                    {/* 미리보기 — 파일 파싱 완료, 아직 업로드 시작 전 */}
                    {parsedItems && !isStarted && (
                      <div className='space-y-3'>
                        <p className='text-sm text-muted-foreground'>
                          파싱 완료 —{' '}
                          <span className='font-medium text-foreground'>{parsedItems.length}건</span>{' '}
                          확인됨
                        </p>
                        <div className='max-h-48 overflow-y-auto rounded-md border'>
                          <Table>
                            <TableHeader>
                              <TableRow>
                                <TableHead className='w-20'>ID</TableHead>
                                <TableHead className='w-48'>제목</TableHead>
                                <TableHead>내용(desc)</TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {parsedItems.map(item => (
                                <TableRow key={String(item.id)}>
                                  <TableCell className='text-muted-foreground'>{item.id}</TableCell>
                                  <TableCell className='font-medium'>{item.title}</TableCell>
                                  <TableCell className='max-w-xs truncate text-sm text-muted-foreground'>
                                    {item.desc.length > 80 ? `${item.desc.slice(0, 80)}...` : item.desc}
                                  </TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </div>
                        <div className='flex gap-2'>
                          <Button onClick={startUpload}>
                            <Upload className='mr-2 h-4 w-4' />
                            업로드 시작 ({parsedItems.length}건)
                          </Button>
                          <Button variant='ghost' onClick={resetBulk}>초기화</Button>
                        </div>
                      </div>
                    )}

                    {/* 진행 목록 — 업로드 시작 후 */}
                    {isStarted && (
                      <div className='space-y-3'>

                        {/* 진행률 바 */}
                        <div className='space-y-1'>
                          <div className='flex items-center justify-between text-sm'>
                            <span className='text-muted-foreground'>
                              {isUploading ? '처리 중...' : '완료'}
                            </span>
                            <span className='font-medium'>
                              {doneCount} / {totalCount}건
                              {successCount > 0 && (
                                <span className='ml-2 text-green-600'>✓{successCount}</span>
                              )}
                              {errorCount > 0 && (
                                <span className='ml-1 text-destructive'>✗{errorCount}</span>
                              )}
                            </span>
                          </div>
                          <div className='h-2 w-full overflow-hidden rounded-full bg-muted'>
                            <div
                              className='h-full bg-primary transition-all duration-300'
                              style={{ width: `${progressPct}%` }}
                            />
                          </div>
                        </div>

                        {/* 건별 상태 목록 */}
                        <div className='max-h-72 overflow-y-auto rounded-md border'>
                          <Table>
                            <TableHeader>
                              <TableRow>
                                <TableHead className='w-10'></TableHead>
                                <TableHead className='w-20'>ID</TableHead>
                                <TableHead>제목</TableHead>
                                <TableHead className='w-24'>DB ID</TableHead>
                                <TableHead>오류</TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {progressItems.map((item, idx) => (
                                <TableRow key={String(item.id) + idx} className={rowBg(item.status)}>
                                  <TableCell>
                                    <StatusIcon status={item.status} />
                                  </TableCell>
                                  <TableCell className='text-muted-foreground'>{item.id}</TableCell>
                                  <TableCell className='font-medium'>{item.title}</TableCell>
                                  <TableCell className='text-muted-foreground'>
                                    {item.documentId ?? '-'}
                                  </TableCell>
                                  <TableCell className='max-w-xs truncate text-xs text-destructive'>
                                    {item.error ?? ''}
                                  </TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </div>

                        {/* 액션 버튼 */}
                        <div className='flex gap-2'>
                          {isUploading ? (
                            <Button variant='destructive' size='sm' onClick={cancelUpload}>
                              취소
                            </Button>
                          ) : (
                            <>
                              {isFinished && (
                                <div className='flex items-center gap-2'>
                                  <Badge variant='secondary'>전체 {totalCount}건</Badge>
                                  {successCount > 0 && (
                                    <Badge className='bg-green-500 text-white hover:bg-green-600'>
                                      성공 {successCount}건
                                    </Badge>
                                  )}
                                  {errorCount > 0 && (
                                    <Badge variant='destructive'>실패 {errorCount}건</Badge>
                                  )}
                                </div>
                              )}
                              <Button variant='outline' size='sm' onClick={resetBulk}>
                                다시 업로드
                              </Button>
                            </>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>

          {/* 저장된 문서 목록 */}
          <Card>
            <CardHeader className='flex flex-row items-center justify-between'>
              <CardTitle className='text-base'>
                저장된 문서
                <Badge variant='secondary' className='ml-2'>{totalElements}건</Badge>
              </CardTitle>
              {documents.length > 0 && (
                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <Button
                      variant='destructive'
                      size='sm'
                      disabled={deleteAllMutation.isPending}
                    >
                      {deleteAllMutation.isPending
                        ? <><Loader2 className='mr-2 h-4 w-4 animate-spin' />삭제 중...</>
                        : <><Trash2 className='mr-2 h-4 w-4' />전체 삭제</>}
                    </Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>전체 문서 삭제</AlertDialogTitle>
                      <AlertDialogDescription>
                        저장된 문서 <strong>{totalElements}건</strong>을 모두 삭제합니다.
                        이 작업은 되돌릴 수 없습니다.
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel>취소</AlertDialogCancel>
                      <AlertDialogAction
                        onClick={() => deleteAllMutation.mutate()}
                        className='bg-destructive text-destructive-foreground hover:bg-destructive/90'
                      >
                        전체 삭제
                      </AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              )}
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className='flex items-center justify-center py-12'>
                  <Loader2 className='h-6 w-6 animate-spin text-muted-foreground' />
                </div>
              ) : documents.length === 0 ? (
                <div className='py-12 text-center text-sm text-muted-foreground'>
                  저장된 문서가 없습니다. 위에서 임베딩을 생성해보세요.
                </div>
              ) : (
                <div className='space-y-3'>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className='w-16'>ID</TableHead>
                        <TableHead className='w-48'>제목</TableHead>
                        <TableHead>내용</TableHead>
                        <TableHead className='w-40'>모델</TableHead>
                        <TableHead className='w-44'>생성일시</TableHead>
                        <TableHead className='w-16'></TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {documents.map(doc => (
                        <TableRow
                          key={doc.id}
                          className='cursor-pointer'
                          onClick={() => { setSelectedDoc(doc); setDocDialogOpen(true) }}
                        >
                          <TableCell className='text-muted-foreground'>{doc.id}</TableCell>
                          <TableCell className='font-medium'>{doc.title}</TableCell>
                          <TableCell className='max-w-xs truncate text-sm text-muted-foreground'>
                            {doc.content.length > 100 ? `${doc.content.slice(0, 100)}...` : doc.content}
                          </TableCell>
                          <TableCell>
                            <Badge variant='outline' className='text-xs'>{doc.model}</Badge>
                          </TableCell>
                          <TableCell className='text-sm text-muted-foreground'>
                            {new Date(doc.createdAt).toLocaleString('ko-KR')}
                          </TableCell>
                          <TableCell onClick={e => e.stopPropagation()}>
                            <AlertDialog>
                              <AlertDialogTrigger asChild>
                                <Button
                                  variant='ghost'
                                  size='icon'
                                  className='h-8 w-8 text-muted-foreground hover:text-destructive'
                                  onClick={() => setDeletingId(doc.id)}
                                >
                                  <Trash2 className='h-4 w-4' />
                                </Button>
                              </AlertDialogTrigger>
                              <AlertDialogContent>
                                <AlertDialogHeader>
                                  <AlertDialogTitle>문서 삭제</AlertDialogTitle>
                                  <AlertDialogDescription>
                                    &quot;{doc.title}&quot; 문서를 삭제합니다. 이 작업은 되돌릴 수 없습니다.
                                  </AlertDialogDescription>
                                </AlertDialogHeader>
                                <AlertDialogFooter>
                                  <AlertDialogCancel onClick={() => setDeletingId(null)}>취소</AlertDialogCancel>
                                  <AlertDialogAction
                                    onClick={() => deleteMutation.mutate(doc.id)}
                                    disabled={deleteMutation.isPending && deletingId === doc.id}
                                    className='bg-destructive text-destructive-foreground hover:bg-destructive/90'
                                  >
                                    {deleteMutation.isPending && deletingId === doc.id ? '삭제 중...' : '삭제'}
                                  </AlertDialogAction>
                                </AlertDialogFooter>
                              </AlertDialogContent>
                            </AlertDialog>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>

                  {/* 페이지네이션 */}
                  {totalPages > 1 && (
                    <div className='flex items-center justify-between border-t pt-3'>
                      <p className='text-sm text-muted-foreground'>
                        {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, totalElements)} / {totalElements}건
                      </p>
                      <div className='flex items-center gap-1'>
                        <Button
                          variant='outline'
                          size='icon'
                          className='h-8 w-8'
                          onClick={() => setPage(p => p - 1)}
                          disabled={page === 0}
                        >
                          <ChevronLeft className='h-4 w-4' />
                        </Button>

                        {getPageNumbers(page, totalPages).map((p, idx) =>
                          p === 'ellipsis' ? (
                            <span key={`ellipsis-${idx}`} className='flex h-8 w-8 items-center justify-center text-sm text-muted-foreground'>
                              …
                            </span>
                          ) : (
                            <Button
                              key={p}
                              variant={p === page ? 'default' : 'outline'}
                              size='icon'
                              className='h-8 w-8 text-sm'
                              onClick={() => setPage(p)}
                            >
                              {p + 1}
                            </Button>
                          )
                        )}

                        <Button
                          variant='outline'
                          size='icon'
                          className='h-8 w-8'
                          onClick={() => setPage(p => p + 1)}
                          disabled={page >= totalPages - 1}
                        >
                          <ChevronRight className='h-4 w-4' />
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </Main>

      {/* 문서 상세 팝업 */}
      <Dialog open={docDialogOpen} onOpenChange={setDocDialogOpen}>
        <DialogContent className='max-w-lg'>
          <DialogHeader>
            <DialogTitle>문서 상세</DialogTitle>
          </DialogHeader>
          <div className='space-y-4 text-sm'>
            <div className='grid grid-cols-[6rem_1fr] gap-y-3'>
              <span className='text-muted-foreground'>ID</span>
              <span className='font-mono'>{selectedDoc?.id}</span>

              <span className='text-muted-foreground'>제목</span>
              <span className='font-medium'>{selectedDoc?.title}</span>

              <span className='text-muted-foreground'>모델</span>
              <Badge variant='outline' className='w-fit text-xs'>{selectedDoc?.model}</Badge>

              <span className='text-muted-foreground'>생성일시</span>
              <span>{selectedDoc ? new Date(selectedDoc.createdAt).toLocaleString('ko-KR') : ''}</span>
            </div>

            <div className='space-y-1'>
              <p className='text-muted-foreground'>내용</p>
              <div className='max-h-64 overflow-y-auto rounded-md border bg-muted/50 p-3 text-sm leading-relaxed whitespace-pre-wrap'>
                {selectedDoc?.content}
              </div>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  )
}
