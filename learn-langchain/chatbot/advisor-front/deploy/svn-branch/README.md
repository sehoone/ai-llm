# svn을 사용해서 개발/운영 관리 전략
- 개발/운영 소스를 관리할때, 예를들어서 A, B, C 반영분이 있을때 A, B, C가 모두 개발에 반영하며 개발하되 A, B만 반영이 필요할떄 있다.
GIT을 사용할때는 브랜치로 분리해서 관리를 하는데 SVN도 비슷하게 관리를 하고자 한다.
- prod(운영) branch > 작업사항 commit > trunk merge > 운영반영(trunk or prod branck 기준)
- dev branch > 작업사항 commit > 개발 반영
- SVN(Subversion)은 Git과는 다른 구조와 워크플로우를 가지고 있다. 일반적으로 다음과 같은 구조를 가진다
```
/repository
  /trunk
  /branches
  /tags
```
- trunk: 주 개발 라인. 일반적으로 최신 개발 버전이 여기에 저장.
- branches: 기능 개발, 버그 수정, 릴리즈 준비 등을 위한 브랜치가 저장.
- tags: 릴리즈 버전이 저장. 태그는 변경되지 않는 스냅샷.

### 1. 브랜치 생성
- 개발/운영 브랜치를 분리해서 생성한다
- svn copy file:///path/to/repository/trunk file:///path/to/repository/branches/prod -m "Creating feature branch"
- totoris svn을 사용할 경우, trunk/project 오른쪽 선택 > totoriseSVN > Branch/Tag.. 선택 > To path항목에 /branches/prod 입력

### 2. checkout or update
- svn checkout file:///path/to/repository/branches/prod /path/to/working/directory
- totoris svn을 사용할 경우, branch 오른쪽 선택 > SVN update

### 3. 변경사항 커밋
- branch에 수정사항을 커밋한다.
```
cd /path/to/working/directory
svn add newfile.txt
svn commit -m "Added newfile.txt"
```

### 4. 브랜치 병합
- 브랜치에 있는 내용을 trunk에 병합한다
- totoris svn을 사용할 경우, trunk/project 오른쪽 선택 > totoriseSVN > merge > URL to merge from에 branch 선택 > all revisions 선택 > merge
```
cd /path/to/working/directory/trunk
svn merge file:///path/to/repository/branches/prod
svn commit -m "Merged changes from prod"
```
