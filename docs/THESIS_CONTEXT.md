> [!IMPORTANT]
> This document is the authoritative research and methodology
> specification for this repository.
>
> If this document conflicts with older protocol documents,
> implementation comments, historical experiment notes, or
> previous research amendments, this document takes precedence.
>
> Implementation must conform to the research design.
> The research design must not be silently changed to fit the
> current implementation.

# Editorial Planning Notes — Non-Normative

> [!NOTE]
> This section contains historical editorial guidance used while
> constructing this research document.
>
> It is preserved for context only and is NOT part of the normative
> research methodology.
>
> Finalized sections beginning with `Project Overview` and the
> subsequent research-design sections define the approved project
> specification.
>
> If an editorial note in this section differs from a finalized
> research decision later in this document, the finalized decision
> takes precedence.

**Project Overview — Tổng quan đề tài.** Viết khoảng 1–2 trang: tên đề tài, background, problem statement, motivation, research gap, objective, research questions (RQ), expected contributions và constraints. Ví dụ problem statement không nên là “Terraform có security issues”, mà gần hơn với: *security scanners tạo ra nhiều findings nhưng severity tĩnh có thể không phản ánh mức ưu tiên trong các deployment context khác nhau*. Đây là phần quan trọng nhất vì mọi thứ phía sau phải phục vụ RQ.  
**Scope — Phạm vi nghiên cứu.** Chốt cực kỳ rõ cái gì làm và không làm. Với thiết kế hiện tại của bạn có thể là: AWS only, Terraform only, static analysis, Checkov, contextual risk prioritization, Random Forest và deterministic baseline; không deploy AWS thật, không làm multi-cloud, không xây LLM, không fine-tune LLM, không làm production platform. Nên chia thành **MUST / SHOULD / OPTIONAL / OUT OF SCOPE** để khi thiếu thời gian biết cắt cái gì trước.  
**Research Model / Conceptual Framework — Mô hình nghiên cứu.** Đây khác system architecture. Bạn cần một sơ đồ giải thích logic khoa học, chẳng hạn `Terraform → Scanner Findings → Context → Prioritization Method → Ranked Findings → Evaluation against Human Ground Truth`. Đồng thời xác định **independent/input variables**, context features, target/label, dependent output và evaluation metrics. Với ML, đây chính là nơi định nghĩa `X = features`, `y = priority score`.  
**System Architecture — Kiến trúc hệ thống.** Sau khi research model rõ mới thiết kế software. Ví dụ kiến trúc mức cao có thể là `Terraform Dataset → Checkov Scanner → Finding Normalizer → Context Extractor/Injector → Feature Builder → Baseline/ML Prioritizer → Ranked Results → Security Gate/Report`. Mỗi component cần biết input/output của nó, nhưng chưa cần thiết kế microservices hay kiến trúc phức tạp.  
**Workflow / Data Flow — Luồng xử lý.** Architecture trả lời **“có những thành phần nào?”**, workflow trả lời **“một artifact đi qua chúng như thế nào?”**. Ví dụ một Terraform sample đi qua Checkov, findings được normalize, ghép với scenario context, chuyển thành feature vector, đưa vào model/scoring, tạo priority score, sort thành ranking, rồi so với human ranking. Nên có cả **training workflow** và **inference/demo workflow**, vì hai cái không hoàn toàn giống nhau.  
**Dataset & Ground Truth Design — Thiết kế dữ liệu.** Trước khi ML phải có kế hoạch dataset: Terraform lấy từ đâu, đơn vị dữ liệu là scenario hay finding, schema dữ liệu, context được gán thế nào, duplicate xử lý ra sao, ground truth do ai annotate, rubric annotation là gì, train/test chia thế nào. Với đề tài của bạn đây có thể là phần rủi ro lớn hơn chính Random Forest, nên cần thiết kế sớm.  
**Methodology & Experimental Design — Phương pháp nghiên cứu/thí nghiệm.** Viết trước khi chạy experiment để tránh kiểu “chạy xong rồi chọn metric nào đẹp”. Ví dụ xác định trước các phương pháp cần so sánh: `B1 severity-only`, `B2 deterministic contextual scoring`, `M1 Random Forest`. Sau đó quy định split theo scenario family, metrics như NDCG`@3/NDCG@5/Spearman`, cách lặp experiment, statistical comparison và secondary experiment như contrastive context. Quan trọng: **không đặt giả thuyết rằng ML bắt buộc phải thắng**.  
**Implementation Design — Thiết kế implementation.** Lúc này mới quyết định repository structure, Python modules, data format JSON/CSV, interface giữa Checkov và Python, preprocessing pipeline, model serialization, CLI, logging, configuration và GitHub Actions demo. Nên ưu tiên pipeline đơn giản, reproducible hơn UI đẹp.  
**Evaluation Plan \+ Threats to Validity — Kế hoạch đánh giá.** Xác định thế nào là kết quả tốt/xấu và đặc biệt **kết quả âm có ý nghĩa gì**. Ví dụ nếu Random Forest không hơn deterministic scoring thì đó vẫn có thể là kết quả nghiên cứu hợp lệ. Đồng thời ghi trước các threats như single annotator, small dataset, circularity giữa context rubric và ML features, source bias, duplicated findings, leakage và limited generalizability.  
**Project Plan — Kế hoạch thực hiện.** Cuối cùng mới chuyển tất cả thành timeline 8–10 tuần. Mỗi tuần phải tạo ra **deliverable kiểm chứng được**, không chỉ “nghiên cứu ML”. Đồng thời đặt kill criteria: chẳng hạn nếu dataset quá nhỏ thì bỏ XGBoost; nếu annotation tốn quá nhiều thời gian thì giảm secondary experiment; nếu ML pipeline không ổn thì giữ RF đơn giản thay vì thêm model; prototype GitHub Actions là thứ có thể cắt trước scientific experiment.

# Project Overview

# **PROJECT OVERVIEW**

## **1\. Project Title**

**Context-Aware Machine Learning for Security Risk Prioritization of Generative AI-Generated Terraform**

**Tên tiếng Việt:**  
**Ứng dụng Machine Learning nhận biết ngữ cảnh để ưu tiên rủi ro bảo mật trong mã Terraform được sinh bởi Generative AI**

---

## **2\. Background**

Infrastructure as Code (IaC) cho phép hạ tầng cloud được định nghĩa, quản lý và triển khai thông qua mã nguồn. Terraform là một trong những công cụ IaC phổ biến, giúp tự động hóa quá trình provisioning và quản lý tài nguyên cloud.

Cùng với sự phát triển của Generative AI, các Large Language Models (LLMs) ngày càng được sử dụng để hỗ trợ sinh mã nguồn, bao gồm cả Terraform. Việc này có thể tăng tốc quá trình phát triển hạ tầng, nhưng mã Terraform do AI sinh ra vẫn có thể chứa các security misconfigurations như:

* tài nguyên bị public ngoài ý muốn;  
* cấu hình IAM có quyền quá rộng;  
* thiếu encryption;  
* thiếu logging hoặc monitoring;  
* cấu hình network không an toàn;  
* cấu hình cloud resource không tuân theo security best practices.

Các Static Application Security Testing (SAST) hoặc IaC security scanners như Checkov có thể phát hiện nhiều loại misconfiguration dựa trên predefined security policies.

Tuy nhiên, việc **phát hiện một security finding** và việc xác định **finding nào cần được xử lý trước** là hai bài toán khác nhau.

Một scanner có thể đưa ra severity dựa chủ yếu trên loại lỗi hoặc policy bị vi phạm, trong khi mức độ ưu tiên thực tế còn phụ thuộc vào ngữ cảnh triển khai của tài nguyên.

Ví dụ, cùng một loại misconfiguration có thể có mức độ ưu tiên khác nhau nếu tài nguyên:

* được public ra Internet;  
* chứa dữ liệu nhạy cảm;  
* thuộc production thay vì development;  
* có vai trò quan trọng đối với hệ thống;  
* được kết hợp với quyền truy cập rộng;  
* có hoặc không có các security controls bổ sung.

Do đó, đề tài tập trung vào việc sử dụng **contextual information kết hợp với Machine Learning** để hỗ trợ ưu tiên các security findings trong Terraform thay vì chỉ dựa vào severity tĩnh của scanner.

---

## **3\. Problem Statement**

Các IaC security scanners có khả năng phát hiện nhiều security misconfigurations trong Terraform. Tuy nhiên, khi số lượng findings lớn, việc xử lý tất cả findings theo cùng một cách hoặc chỉ dựa trên scanner severity có thể chưa phản ánh đầy đủ mức độ ưu tiên trong từng deployment context.

Vấn đề nghiên cứu chính của đề tài là:

> **Làm thế nào để sử dụng thông tin ngữ cảnh của hạ tầng kết hợp với Machine Learning nhằm ưu tiên các security findings trong Terraform theo mức độ rủi ro thực tế hơn so với việc chỉ sử dụng severity tĩnh từ security scanner?**

Đề tài không tập trung xây dựng một vulnerability scanner mới. Thay vào đó, kết quả từ security scanner được sử dụng như đầu vào cho một **context-aware risk prioritization layer**.

---

## **4\. Motivation**

Trong quy trình DevSecOps, một trong những khó khăn không chỉ là phát hiện security issues mà còn là quyết định:

> **Which security issue should be fixed first?**

Khi một hệ thống tạo ra nhiều security alerts, developer hoặc security engineer có thể gặp tình trạng alert overload. Nếu tất cả findings chỉ được sắp xếp dựa trên một severity chung mà không xét đến deployment context, một finding có ảnh hưởng lớn trong một tình huống cụ thể có thể không được ưu tiên phù hợp.

Do đó, một cơ chế prioritization có khả năng xem xét context có thể giúp:

* giảm lượng findings mà developer phải xem xét ngay lập tức;  
* đưa các findings quan trọng hơn lên đầu danh sách;  
* hỗ trợ quyết định remediation;  
* cung cấp giải thích về lý do một finding được ưu tiên;  
* hỗ trợ tích hợp security prioritization vào DevSecOps workflow.

---

## **5\. Research Gap / Research Opportunity**

Các security scanners có thể cung cấp rule, category và severity cho security findings. Tuy nhiên, severity của một finding không nhất thiết đại diện đầy đủ cho **context-dependent risk**.

Ví dụ:

Same Misconfiguration  
        │  
        ├── Development \+ Private \+ Test Data  
        │          ↓  
        │     Lower Priority  
        │  
        └── Production \+ Public \+ Sensitive Data  
                   ↓  
              Higher Priority

Điều này tạo ra cơ hội nghiên cứu một phương pháp trong đó security finding được đánh giá không chỉ dựa trên đặc điểm của misconfiguration mà còn dựa trên **deployment context**.

Đề tài sẽ khảo sát liệu contextual features kết hợp với Machine Learning có thể cải thiện việc prioritization so với các phương pháp baseline đơn giản hay không.

**Lưu ý:** Research gap này là giả thuyết ban đầu của đề tài và cần được xác nhận thêm thông qua literature review.

---

## **6\. Research Aim**

Mục tiêu tổng quát của đề tài là:

> **Thiết kế và đánh giá một phương pháp context-aware sử dụng Machine Learning để ưu tiên các security findings trong Terraform, đặc biệt trong bối cảnh Terraform artifacts được sinh bởi Generative AI.**

Hệ thống hướng tới việc chuyển đổi:

Security Findings

thành:

Context-Aware Prioritized Security Findings

để hỗ trợ developer hoặc security engineer xác định các vấn đề cần xử lý trước.

---

## **7\. Research Objectives**

Đề tài đặt ra các mục tiêu chính sau:

**O1 — Xây dựng tập dữ liệu Terraform security findings**

Thu thập hoặc tạo Terraform artifacts, bao gồm các artifacts được sinh bởi Generative AI, sau đó sử dụng security scanner để phát hiện các security misconfigurations.

**O2 — Xây dựng mô hình biểu diễn security context**

Xác định và trích xuất các contextual features có khả năng ảnh hưởng đến mức độ ưu tiên của security finding, chẳng hạn như:

* environment;  
* Internet exposure;  
* data sensitivity;  
* resource criticality;  
* IAM exposure;  
* encryption;  
* logging;  
* network configuration.

**O3 — Xây dựng ground truth cho risk prioritization**

Thiết kế một annotation/risk assessment rubric để xác định mức độ ưu tiên kỳ vọng của các findings dựa trên security context.

**O4 — Xây dựng context-aware prioritization model**

Sử dụng contextual features và thông tin security finding để huấn luyện một Machine Learning model có khả năng tạo priority score hoặc ranking cho các findings.

**O5 — Xây dựng các baseline methods**

So sánh ML approach với các phương pháp đơn giản hơn, chẳng hạn:

* scanner severity-based prioritization;  
* deterministic/rule-based contextual scoring.

**O6 — Đánh giá hiệu quả của phương pháp**

Đánh giá khả năng ranking/prioritization của các phương pháp so với ground truth bằng các metrics phù hợp.

**O7 — Xây dựng prototype**

Xây dựng một prototype cho phép đưa Terraform artifact vào pipeline và nhận lại danh sách security findings đã được ưu tiên.

---

## **8\. Research Questions**

### **RQ1 — Context**

> **Which contextual factors are useful for determining the priority of security findings in Terraform infrastructure?**

Mục tiêu của RQ1 là xác định những context features nào có ý nghĩa đối với security prioritization.

### **RQ2 — Context-aware Prioritization**

> **Does incorporating deployment context improve security finding prioritization compared with scanner severity alone?**

RQ2 đánh giá giá trị của context thay vì chỉ sử dụng severity do scanner cung cấp.

### **RQ3 — Machine Learning**

> **Can a Machine Learning-based prioritization approach provide better ranking performance than deterministic context-based scoring?**

RQ3 nhằm kiểm tra liệu ML có thực sự tạo thêm giá trị hay một rule-based approach đơn giản đã đủ hiệu quả.

### **RQ4 — Explainability**

> **Which contextual factors contribute most to the prioritization decisions made by the model?**

RQ4 giúp phân tích vai trò của từng contextual feature và tăng khả năng giải thích kết quả.

---

## **9\. Proposed Approach**

Pipeline tổng quát của đề tài:

Terraform Artifacts  
        │  
        ▼  
IaC Security Scanner  
        │  
        ▼  
Raw Security Findings  
        │  
        ▼  
Finding Normalization  
        │  
        ├──────────────┐  
        ▼              ▼  
Infrastructure      Deployment  
Information          Context  
        │              │  
        └──────┬───────┘  
               ▼  
        Feature Extraction  
               │  
               ▼  
        Feature Dataset  
               │  
       ┌───────┼───────────┐  
       ▼       ▼           ▼  
   Scanner   Rule-based    ML-based  
   Severity   Context      Prioritization  
   Baseline   Baseline  
       │       │           │  
       └───────┼───────────┘  
               ▼  
        Ranked Findings  
               │  
               ▼  
         Evaluation  
               │  
               ▼  
        Research Results

Ba phương pháp chính được so sánh:

**Baseline 1 — Scanner Severity**

Ưu tiên findings dựa trên severity có sẵn từ security scanner.

**Baseline 2 — Deterministic Context-Aware Scoring**

Sử dụng các security rules được định nghĩa trước để kết hợp severity và contextual information.

**Proposed Method — ML-based Context-Aware Prioritization**

Machine Learning model học mối quan hệ giữa finding/context features và ground-truth priority.

Việc so sánh ba phương pháp giúp xác định liệu:

Context \> Scanner Severity?

và:

Machine Learning \> Simple Context Rules?  
---

## **10\. Initial Scope**

Để giữ đề tài khả thi trong phạm vi đồ án tốt nghiệp, phiên bản ban đầu giới hạn như sau:

### **In Scope**

* Infrastructure as Code;  
* Terraform;  
* cloud security misconfigurations;  
* Terraform artifacts, bao gồm GenAI-generated Terraform;  
* static security analysis;  
* security finding normalization;  
* contextual feature extraction;  
* context-aware security risk prioritization;  
* Machine Learning-based prioritization;  
* comparison với baseline approaches;  
* experimental evaluation;  
* prototype demonstrating the prioritization workflow.

### **Out of Scope**

Đề tài không đặt mục tiêu:

* xây dựng vulnerability scanner hoàn toàn mới;  
* phát hiện mọi loại cloud vulnerability;  
* phân tích source code application truyền thống;  
* thay thế hoàn toàn security expert;  
* xây dựng hoặc huấn luyện một Large Language Model mới;  
* giải quyết toàn bộ bài toán cloud security;  
* xây dựng một production-grade commercial security platform.

Phạm vi cụ thể về cloud provider, scanner, loại resources, số lượng misconfiguration và ML algorithms sẽ được cố định sau giai đoạn dataset exploration và literature review.

---

## **11\. Expected Contributions**

Đề tài kỳ vọng tạo ra các đóng góp sau:

### **C1 — Context-aware representation**

Một cách biểu diễn security finding kết hợp thông tin về misconfiguration với deployment context.

### **C2 — Security prioritization dataset**

Một dataset gồm Terraform security findings, contextual features và ground-truth priority labels/rankings phục vụ thực nghiệm.

### **C3 — Context-aware prioritization approach**

Một phương pháp sử dụng Machine Learning để tạo priority score hoặc ranking cho security findings.

### **C4 — Empirical comparison**

Thực nghiệm so sánh:

Scanner Severity  
        vs  
Rule-based Context Scoring  
        vs  
ML-based Context Prioritization

nhằm xác định giá trị thực tế của context và Machine Learning.

### **C5 — Feature importance analysis**

Phân tích contextual factors nào ảnh hưởng nhiều nhất đến kết quả prioritization.

### **C6 — Prototype**

Một prototype thể hiện toàn bộ pipeline từ Terraform artifact đến prioritized security findings và có khả năng minh họa cách phương pháp có thể được tích hợp vào DevSecOps workflow.

---

## **12\. Expected Outputs**

Các sản phẩm cuối cùng dự kiến bao gồm:

1. Terraform security dataset;  
2. normalized security findings dataset;  
3. contextual feature schema;  
4. ground-truth annotation/risk assessment rubric;  
5. deterministic prioritization baseline;  
6. Machine Learning prioritization model;  
7. experimental evaluation results;  
8. feature importance/explainability analysis;  
9. prototype prioritization pipeline;  
10. thesis/report và source code.

---

## **13\. Evaluation Direction**

Việc đánh giá tập trung vào khả năng **prioritization/ranking**, thay vì chỉ đánh giá classification accuracy.

Các nhóm metrics có thể được xem xét bao gồm:

* ranking quality;  
* Precision/Recall/F1 khi chuyển bài toán sang priority classes;  
* Precision@K;  
* Recall@K;  
* NDCG@K;  
* rank correlation như Spearman correlation.

Experimental design cuối cùng sẽ lựa chọn metrics phù hợp với cách ground truth được định nghĩa.

Kết quả của ML model sẽ được so sánh với baseline để trả lời các Research Questions.

Một kết quả trong đó ML không vượt trội deterministic baseline vẫn được xem là một kết quả nghiên cứu có giá trị nếu thí nghiệm được thiết kế và đánh giá đúng, vì nó cung cấp bằng chứng về mức độ cần thiết của ML đối với bài toán prioritization này.

---

## **14\. Key Research Challenges**

Đề tài dự kiến có bốn thách thức chính.

**Ground Truth**

“Actual risk priority” không có sẵn trực tiếp. Cần xây dựng annotation methodology đủ rõ ràng và hạn chế subjective bias.

**Context Modeling**

Cần xác định context nào thực sự ảnh hưởng đến security risk thay vì thêm nhiều features nhưng không mang ý nghĩa bảo mật.

**Data Leakage**

Nếu model được cung cấp trực tiếp scanner severity, rule identifier hoặc các features có quan hệ quá gần với label, model có thể đạt kết quả cao nhưng chỉ đang học lại scoring logic đã có.

**ML Value**

Cần chứng minh ML có tạo thêm giá trị so với một deterministic rule-based scoring system hay không.

Vì vậy, thành công của đề tài không được định nghĩa đơn giản là “ML đạt accuracy cao”, mà là khả năng đưa ra bằng chứng thực nghiệm đáng tin cậy về giá trị của context và Machine Learning đối với security risk prioritization.

---

## **15\. Success Criteria**

Đề tài được xem là đạt mục tiêu nghiên cứu khi có thể:

* xây dựng được một dataset có cấu trúc và ground truth rõ ràng;  
* xác định được một tập contextual features có cơ sở về security;  
* triển khai được ít nhất một baseline không sử dụng ML;  
* xây dựng được một ML prioritization model;  
* thực hiện được comparison experiment công bằng giữa các approaches;  
* đánh giá được kết quả bằng ranking/classification metrics phù hợp;  
* phân tích được ảnh hưởng của contextual features;  
* thảo luận được limitations và threats to validity;  
* xây dựng được prototype chứng minh end-to-end workflow.

---

## **16\. Project Summary**

Đề tài nghiên cứu phương pháp **context-aware security risk prioritization** cho Terraform, đặc biệt trong bối cảnh mã Infrastructure as Code được sinh bởi Generative AI.

Thay vì chỉ phát hiện security misconfigurations, hệ thống sử dụng kết quả từ security scanner kết hợp với deployment context để xác định **finding nào nên được xử lý trước**.

Machine Learning được sử dụng như một phương pháp prioritization và được đánh giá thông qua so sánh với scanner severity và deterministic context-aware scoring.

Mục tiêu cuối cùng không phải chứng minh rằng Machine Learning luôn tốt hơn, mà là cung cấp bằng chứng thực nghiệm về:

> **khi nào context cải thiện security prioritization, contextual factors nào quan trọng, và liệu Machine Learning có tạo thêm giá trị so với các phương pháp scoring đơn giản hơn hay không.**

Tóm tắt ý tưởng của đề tài:

> **Scanner finds the issue. Context describes its situation. Machine Learning helps prioritize what should be fixed first.**

# SCOPE — PHẠM VI NGHIÊN CỨU

# **SCOPE — PHẠM VI NGHIÊN CỨU**

## **1\. Mục đích xác định phạm vi**

Đề tài **Context-Aware Machine Learning for Security Risk Prioritization of Generative-AI-Generated Terraform** được thực hiện bởi một sinh viên trong thời gian giới hạn. Vì vậy, phạm vi nghiên cứu được thiết kế theo nguyên tắc:

> **Research first, prototype second.**

Mục tiêu không phải xây dựng một nền tảng Cloud Security hoặc DevSecOps hoàn chỉnh, mà tập trung trả lời một bài toán nghiên cứu cụ thể:

> **Liệu thông tin ngữ cảnh có giúp ưu tiên các security findings trong Terraform tốt hơn severity-only hay không, và Machine Learning có tạo thêm giá trị so với deterministic contextual scoring hay không?**

Do đó, mọi thành phần không trực tiếp phục vụ câu hỏi nghiên cứu này được xem là secondary, optional hoặc out of scope.

---

# **2\. Research Scope**

## **2.1. Research Core**

Phạm vi nghiên cứu cốt lõi được giới hạn ở:

Terraform Security Findings  
          \+  
Infrastructure / Business Context  
          ↓  
Security Risk Prioritization  
          ↓  
Severity Baseline  
vs  
Contextual Rule Baseline  
vs  
Machine Learning  
          ↓  
Empirical Evaluation

Đề tài tập trung vào **prioritization**, không tập trung phát triển một phương pháp vulnerability detection mới.

Security scanner chịu trách nhiệm phát hiện các security findings.

Phần nghiên cứu của đề tài bắt đầu chủ yếu từ:

Security Findings  
        ↓  
Context Representation  
        ↓  
Priority Estimation  
        ↓  
Ranking  
        ↓  
Evaluation  
---

# **3\. Infrastructure-as-Code Scope**

## **3.1. IaC Technology**

Đề tài chỉ nghiên cứu:

> **Terraform**

Không mở rộng sang:

* AWS CloudFormation;  
* Pulumi;  
* Ansible;  
* Kubernetes manifests;  
* Helm;  
* Chef;  
* Puppet;  
* các IaC framework khác.

Việc giới hạn một IaC technology giúp giảm variation trong syntax, resource representation và scanner behavior.

---

# **4\. Cloud Scope**

## **4.1. Cloud Provider**

Đề tài giới hạn ở:

> **Amazon Web Services — AWS**

Không thực hiện comparative study giữa:

AWS vs Azure vs GCP

và không tuyên bố kết quả có thể trực tiếp generalize sang mọi cloud provider.

## **4.2. Deployment**

Đề tài chủ yếu thực hiện **static analysis**.

Không yêu cầu triển khai infrastructure thật lên AWS.

Terraform artifacts có thể được:

terraform init  
        ↓  
terraform validate  
        ↓  
Security Scan

và sử dụng `terraform plan` trong trường hợp cần thiết và khả thi.

Không yêu cầu:

terraform apply

trên AWS production environment.

Điều này giúp giảm:

* chi phí cloud;  
* credential management;  
* operational risk;  
* complexity;  
* dependency vào AWS runtime environment.

---

# **5\. Security Analysis Scope**

## **5.1. Security Scanner**

Security scanner chính:

> **Checkov**

Checkov được sử dụng để:

Terraform  
    ↓  
Checkov  
    ↓  
Raw Security Findings

Đề tài không nhằm xây dựng scanner mới và không đánh giá toàn diện scanner nào tốt nhất.

Scanner khác chỉ được xem xét khi có lý do nghiên cứu rõ ràng và không ảnh hưởng đến tiến độ của core experiment.

## **5.2. Security Finding**

Đơn vị nghiên cứu chính ở mức dữ liệu là:

> **Security finding**

Một finding đại diện cho một security policy violation hoặc security-related misconfiguration được phát hiện trong Terraform artifact.

Cần phân biệt:

Scanner Finding  
      ≠  
Independent Real-World Vulnerability

Nhiều scanner findings có thể liên quan đến cùng một underlying Terraform root cause.

Vì vậy, kết quả nghiên cứu được diễn giải là:

> **prioritization of security scanner findings**

thay vì tuyên bố mỗi finding là một vulnerability độc lập.

---

# **6\. Security Categories**

Đề tài không cố gắng bao phủ toàn bộ AWS security landscape.

Nghiên cứu tập trung vào một tập hữu hạn các security categories có thể được xác định từ Terraform và Checkov evidence.

Các nhóm candidate có thể bao gồm:

* public resource exposure;  
* overly permissive network access;  
* open administrative ports;  
* IAM wildcard permissions;  
* excessive privilege;  
* missing encryption;  
* missing logging;  
* insecure access configuration.

Danh sách category cuối cùng được freeze dựa trên research corpus thực tế.

Không mở rộng category chỉ nhằm tăng kích thước dataset hoặc cải thiện ML metrics.

---

# **7\. Generative AI Scope**

## **7.1. Vai trò của Generative AI**

Generative AI được sử dụng chủ yếu như:

> **nguồn của experimental Terraform artifacts**

Pipeline conceptual:

Prior Work / Generative AI  
          ↓  
AI-generated Terraform  
          ↓  
Security Analysis  
          ↓  
Security Findings

Generative AI **không phải biến nghiên cứu chính**.

Đề tài không đặt câu hỏi:

> Model LLM nào sinh Terraform tốt nhất?

và không yêu cầu so sánh nhiều LLM.

## **7.2. Không phụ thuộc Runtime LLM**

Research pipeline không phụ thuộc vào:

* GPT API;  
* Gemini API;  
* Claude API;  
* local LLM;  
* commercial Generative AI API.

Terraform artifacts được lưu offline và có thể tái sử dụng để bảo đảm reproducibility.

Không thực hiện:

* LLM fine-tuning;  
* Transformer training;  
* prompt optimization research;  
* LLM agent;  
* RAG;  
* multi-agent systems.

---

# **8\. Dataset Scope**

## **8.1. Dataset Strategy**

Đề tài ưu tiên:

> **Reuse → Reproduce → Extend → Evaluate**

thay vì tự xây toàn bộ dataset từ đầu.

Candidate Terraform artifacts có thể được lấy từ:

* benchmark đã được công bố;  
* research artifacts từ prior work;  
* public/reproducible AI-generated Terraform sources;  
* một lượng controlled scenarios bổ sung khi thật sự cần thiết.

Các artifacts phải có provenance đủ rõ và đáp ứng các điều kiện sử dụng phù hợp.

## **8.2. Research Corpus**

Artifact được đưa vào research corpus khi đáp ứng các tiêu chí chính như:

AWS  
AND  
Terraform  
AND  
Technically Valid  
AND  
Checkov Scanable  
AND  
Known Provenance  
AND  
Acceptable Usage / License  
AND  
At Least One In-Scope Finding

Research corpus có thể lớn hơn dataset thực sự dùng cho human prioritization.

## **8.3. Prioritization Benchmark**

Không bắt buộc human annotate toàn bộ research corpus.

Thay vào đó:

Large Research Corpus  
        ↓  
Predefined Selection Criteria  
        ↓  
Smaller Prioritization Benchmark  
        ↓  
Human Annotation  
        ↓  
ML / Baseline Evaluation

Prioritization benchmark cần ưu tiên:

* finding density;  
* security-category diversity;  
* resource diversity;  
* source diversity;  
* context relevance;  
* scenario-family diversity.

Không lựa chọn scenario dựa trên việc scenario đó làm cho ML đạt metric tốt hơn.

## **8.4. Dataset Size**

Không đặt một con số cứng làm điều kiện thành công của đề tài.

Các target dataset được xem là:

> **planning targets, not mandatory scientific requirements.**

Ưu tiên:

Dataset Quality  
      \>  
Dataset Size

Một benchmark nhỏ hơn nhưng:

* có đủ findings để ranking;  
* có context variation;  
* ground truth đáng tin;  
* không leakage;  
* có đủ diversity;

được ưu tiên hơn benchmark lớn nhưng annotation hoặc methodology yếu.

---

# **9\. Context Scope**

Context được chia thành hai lớp.

## **9.1. Scenario-Level / Business Context**

Các candidate features chính:

environment  
asset\_criticality  
data\_sensitivity

Ví dụ:

environment: production  
asset\_criticality: high  
data\_sensitivity: high

Các giá trị này phải được cung cấp bằng explicit metadata.

Không suy luận business context chủ yếu từ resource name.

Ví dụ không tự động kết luận:

payment\_database  
      ↓  
critical \= true

chỉ vì resource chứa từ `payment`.

## **9.2. Finding / Resource-Level Context**

Các candidate features chính:

internet\_exposure  
privilege\_impact  
reachability

Có thể bổ sung các objective infrastructure facts khi có evidence rõ ràng, chẳng hạn:

public\_access  
wildcard\_action  
wildcard\_resource  
encryption\_missing  
logging\_missing  
resource\_type  
resource\_role

Feature chỉ được sử dụng nếu có thể suy ra hợp lý từ:

Terraform  
or  
Scanner Evidence  
or  
Explicit Scenario Metadata

Không tạo feature dựa trên model prediction hoặc human rank.

---

# **10\. Ground Truth Scope**

Ground truth của nghiên cứu là:

> **Contextual security priority under the predefined study methodology.**

Ground truth **không được diễn giải là**:

* xác suất hệ thống thực sự bị compromise;  
* absolute real-world risk;  
* universal security truth.

Trong mỗi scenario, human annotator đánh giá relative priority của các in-scope findings.

Ví dụ:

Scenario X

Finding A → Rank 1  
Finding B → Rank 2  
Finding C → Rank 3  
Finding D → Rank 4

Annotation phải được thực hiện mà không xem:

* ML prediction;  
* Random Forest result;  
* contextual baseline result;  
* NDCG result;  
* final evaluation metrics.

Nếu chỉ có một annotator, nghiên cứu phải công bố đây là:

> **single-annotator ground truth**

và xem đây là limitation.

Second annotator hoặc expert review được xem là desirable nhưng không được để toàn bộ thesis phụ thuộc vào việc có external expert.

---

# **11\. Machine Learning Scope**

## **11.1. ML Problem**

Bài toán chính được mô hình hóa ở mức đơn giản:

> **Pointwise priority scoring / regression**

Input:

Security Finding  
        \+  
Security / Infrastructure Context  
        \+  
Business Context

Output:

Continuous Priority Score

Sau đó:

Priority Score  
      ↓  
Sort Descending  
      ↓  
Predicted Ranking

## **11.2. Primary ML Model**

Model chính:

> **Random Forest Regressor**

Random Forest được chọn nhằm giữ ML pipeline:

* dễ triển khai;  
* phù hợp tabular data;  
* không yêu cầu GPU;  
* tương đối dễ giải thích;  
* phù hợp phạm vi một đồ án sinh viên.

## **11.3. Optional ML Model**

> **XGBoost Regressor — OPTIONAL**

Chỉ thực hiện khi:

* Random Forest pipeline đã ổn định;  
* dataset đã freeze;  
* baseline đã hoàn thành;  
* evaluation chạy được;  
* còn đủ thời gian.

XGBoost không phải điều kiện bắt buộc để hoàn thành đề tài.

## **11.4. Không sử dụng**

Không thực hiện trong phiên bản chính:

* Deep Learning;  
* neural networks;  
* Transformer;  
* LLM fine-tuning;  
* reinforcement learning;  
* complex ensemble;  
* XGBRanker;  
* Learning-to-Rank chuyên sâu.

Learning-to-Rank có thể được đề cập trong future work.

---

# **12\. Baseline Scope**

Machine Learning không được đánh giá một cách độc lập.

Phải có tối thiểu hai baseline.

## **Baseline A — Severity-Only**

Security Finding  
       ↓  
Severity  
       ↓  
Ranking

Mục đích:

> kiểm tra phương pháp prioritization truyền thống chỉ dựa trên severity.

## **Baseline B — Deterministic Contextual Scoring**

Severity  
   \+  
Finding-Level Context  
   \+  
Business Context  
       ↓  
Rule-Based Score  
       ↓  
Ranking

Mục đích:

> kiểm tra liệu chỉ cần một contextual rule-based system đã đủ hay chưa.

## **Proposed ML Method**

Finding \+ Context Features  
       ↓  
Random Forest  
       ↓  
Priority Score  
       ↓  
Ranking

Main comparison:

Severity Only  
      vs  
Context Rule  
      vs  
Random Forest

ML **không bắt buộc phải thắng** để nghiên cứu được xem là thành công.

---

# **13\. Training / Testing Scope**

Không sử dụng random finding-level split khi findings thuộc cùng một scenario family.

Split phải giữ các related scenarios cùng một group.

Ví dụ:

Family 01  
├── Context A  
└── Context B

phải cùng thuộc:

TRAIN

hoặc:

TEST

Không được:

Context A → TRAIN  
Context B → TEST

Các phương pháp candidate:

* GroupKFold;  
* Leave-One-Family-Out;  
* group-based train/test split.

Mục tiêu là hạn chế train-test leakage.

---

# **14\. Evaluation Scope**

Đề tài tập trung đánh giá **ranking quality**.

## **Primary Metrics**

Candidate primary metrics:

NDCG@3  
NDCG@5

## **Secondary Metric**

Spearman Rank Correlation

## **Diagnostic Metrics**

Có thể sử dụng:

MAE  
RMSE

nhưng đây không phải tiêu chí chính để đánh giá ranking quality.

## **Statistical Comparison**

Khi dataset và số scenario cho phép, có thể sử dụng:

* paired comparison;  
* Wilcoxon signed-rank test;  
* effect size;  
* bootstrap confidence interval.

Statistical analysis phải phù hợp với kích thước dataset thực tế và không được overclaim significance khi sample nhỏ.

---

# **15\. Contrastive Context Analysis**

Contrastive experiment được xem là:

> **Secondary Analysis**

Ý tưởng:

Same Terraform  
Same Security Finding  
        │  
        ├── Context A  
        │   Development  
        │   Low Criticality  
        │  
        └── Context B  
            Production  
            High Criticality

Sau đó kiểm tra:

score(Context B) \- score(Context A)

để phân tích model có phản ứng với thay đổi context hay không.

Contrastive analysis không được ưu tiên hơn main experiment.

Nếu thời gian không đủ, có thể giảm quy mô hoặc chuyển phần này thành supplementary analysis.

---

# **16\. Explainability Scope**

Explainability chỉ thực hiện ở mức phù hợp với tabular ML.

Có thể sử dụng:

* Random Forest feature importance;  
* permutation importance;  
* minimal feature ablation.

Ví dụ:

All Features  
      vs  
Without Business Context

hoặc:

All Features  
      vs  
Without Internet Exposure

Không xây dựng một explainable-AI framework phức tạp.

---

# **17\. Prototype Scope**

Prototype được xây dựng để chứng minh khả năng ứng dụng kết quả nghiên cứu vào DevSecOps.

Pipeline:

Terraform  
    ↓  
Checkov  
    ↓  
Finding Normalization  
    ↓  
Context / Feature Extraction  
    ↓  
Priority Scoring  
    ↓  
Ranking  
    ↓  
Security Gate

Output có thể gồm:

finding  
check\_id  
resource  
priority\_score  
rank  
context  
gate\_status

Interface tối thiểu:

CLI  
\+  
JSON

GitHub Actions integration được thực hiện nếu core research đã hoàn thành.

Prototype không phải production security platform.

---

# **18\. Security Gate Scope**

Security Gate có thể ánh xạ prioritized findings thành operational decision:

Low Priority  
     ↓  
PASS

Medium Priority  
     ↓  
WARN

High Priority  
     ↓  
REVIEW

Very High Priority  
     ↓  
BLOCK

Các threshold này được xem là:

> **operational policy**

không phải scientific ground truth.

Security Gate chỉ là application layer chứng minh cách prioritization approach có thể được tích hợp vào DevSecOps workflow.

---

# **19\. MUST / SHOULD / OPTIONAL**

Để kiểm soát scope, các thành phần được chia thành ba mức.

## **MUST — Bắt buộc**

AWS  
Terraform  
Static Analysis  
Checkov  
Research Corpus  
Finding Normalization  
Context Feature Schema  
Ground Truth  
Severity Baseline  
Context Baseline  
Random Forest  
Group-Based Split  
NDCG@3 / NDCG@5  
Basic Ranking Evaluation  
Research Results  
Limitations / Threats to Validity  
Minimal CLI/JSON Prototype

Nếu các thành phần này hoàn thành, core thesis được xem là có thể hoàn chỉnh.

## **SHOULD — Nên thực hiện**

Spearman  
Basic Statistical Comparison  
Feature Importance  
Minimal Ablation  
Contrastive Context Analysis  
Second-annotator / Expert Review trên subset nếu khả thi  
GitHub Actions Security Gate

Các phần này tăng chất lượng nghiên cứu nhưng không được phép làm chậm core experiment.

## **OPTIONAL — Chỉ làm nếu còn thời gian**

XGBoost  
Additional Terraform Sources  
Larger Dataset  
Additional Context Features  
Additional Visualization  
PR Comment Integration  
Additional Statistical Analysis

OPTIONAL không được biến thành deadline bắt buộc.

---

# **20\. Explicitly Out of Scope**

Các thành phần sau **không thuộc phạm vi phiên bản chính**:

❌ Multi-cloud comparison  
❌ Azure  
❌ GCP  
❌ Kubernetes security  
❌ Runtime LLM  
❌ RAG  
❌ MCP  
❌ Multi-agent system  
❌ LLM fine-tuning  
❌ Transformer training  
❌ Deep Learning  
❌ Attack graph  
❌ Full attack-path reasoning  
❌ SIEM integration  
❌ Autonomous remediation  
❌ Production exploitation  
❌ Real AWS production deployment  
❌ Complex dashboard  
❌ Full web application  
❌ Scanner benchmark study  
❌ Large-scale LLM comparison  
❌ Building an IaC scanner from scratch  
❌ Building a production-grade DevSecOps platform

Các hướng này có thể được đề cập trong Future Work nhưng không được thêm vào implementation nếu core research chưa hoàn thành.

---

# **21\. Scope Firewall**

Khi xuất hiện ý tưởng mới trong quá trình thực hiện, sử dụng quy tắc:

Ý tưởng mới  
    ↓  
Có trực tiếp giúp trả lời RQ?  
    │  
 ┌──┴───┐  
 NO     YES  
 │       │  
 ▼       ▼  
Reject   Có cần để hoàn thành  
         main experiment?  
             │  
          ┌──┴───┐  
          NO     YES  
          │       │  
          ▼       ▼  
       Future    Consider  
        Work

Không thêm feature chỉ vì:

* công nghệ đó đang phổ biến;  
* muốn demo trông phức tạp hơn;  
* muốn đề tài có nhiều AI hơn;  
* muốn tăng số lượng công nghệ trong CV;  
* metric hiện tại chưa đẹp.

---

# **22\. Scope Reduction Order**

Nếu thiếu thời gian, cắt theo thứ tự:

1\. Additional visualization  
        ↓  
2\. Extra dataset expansion  
        ↓  
3\. XGBoost  
        ↓  
4\. Advanced explainability  
        ↓  
5\. GitHub Actions integration  
        ↓  
6\. Contrastive secondary analysis

Không cắt trước:

Ground Truth  
Dataset QA  
Baselines  
Random Forest  
Leakage Prevention  
Main Evaluation  
Threats to Validity

vì đây là các thành phần trực tiếp quyết định tính hợp lệ của nghiên cứu.

---

# **23\. Research Boundary**

Đề tài chỉ đưa ra kết luận trong phạm vi:

Selected AI-generated  
AWS Terraform Artifacts  
        \+  
Selected Security Categories  
        \+  
Checkov Findings  
        \+  
Defined Context Representation  
        \+  
Study Ground Truth

Do đó không tuyên bố:

> “ML có thể ưu tiên chính xác mọi cloud security vulnerability.”

Thay vào đó, conclusion cần được giới hạn ở dạng:

> “Trong benchmark và contextual representation được nghiên cứu, phương pháp X đạt kết quả Y so với severity-only và deterministic contextual baseline.”

---

# **24\. Scope Success Criteria**

Phạm vi được xem là hoàn thành khi nghiên cứu có thể tạo được pipeline:

Terraform Corpus  
       ↓  
Security Findings  
       ↓  
Normalized Findings  
       ↓  
Context Features  
       ↓  
Human Ground Truth  
       ↓  
┌─────────────┬───────────────┬──────────────┐  
│ Severity    │ Context Rule  │ Random Forest│  
└──────┬──────┴───────┬───────┴──────┬───────┘  
       └──────────────┼───────────────┘  
                      ↓  
               Predicted Rankings  
                      ↓  
               Ranking Evaluation  
                      ↓  
                Research Result

và có thể trả lời được tối thiểu hai câu hỏi:

> **Context có cải thiện prioritization so với severity-only hay không?**

và:

> **Machine Learning có tạo thêm giá trị so với deterministic contextual scoring hay không?**

Không yêu cầu kết quả phải chứng minh Random Forest tốt hơn baseline.

Negative result vẫn được xem là kết quả nghiên cứu hợp lệ nếu dataset, ground truth, experimental protocol và evaluation được xây dựng hợp lý.

---

# **25\. Scope Summary**

Phạm vi chính thức của đề tài có thể tóm tắt như sau:

> **Nghiên cứu tập trung vào việc ưu tiên các security findings được phát hiện bởi Checkov trong AWS Terraform artifacts, đặc biệt là Terraform được sinh bởi Generative AI. Các findings được biểu diễn bằng scanner information, objective infrastructure/security facts và explicit business context. Nghiên cứu so sánh severity-only prioritization, deterministic context-aware scoring và Random Forest-based prioritization bằng các ranking metrics trên human-annotated ground truth. Generative AI đóng vai trò nguồn experimental artifacts, trong khi Machine Learning là phương pháp được đánh giá. Một lightweight DevSecOps Security Gate được xây dựng như prototype minh họa khả năng ứng dụng, không phải scientific contribution chính.**

# RESEARCH MODEL / CONCEPTUAL FRAMEWORK

# **RESEARCH MODEL / CONCEPTUAL FRAMEWORK**

## **1\. Purpose of the Conceptual Framework**

Mô hình nghiên cứu của đề tài **Context-Aware Machine Learning for Security Risk Prioritization of Generative-AI-Generated Terraform** mô tả mối quan hệ giữa:

* security findings được phát hiện trong Terraform;  
* ngữ cảnh của infrastructure và deployment;  
* phương pháp prioritization;  
* priority score/ranking được tạo ra;  
* human-defined ground truth;  
* kết quả đánh giá chất lượng prioritization.

Mục tiêu của mô hình không phải chứng minh trước rằng Machine Learning tốt hơn phương pháp truyền thống.

Thay vào đó, nghiên cứu kiểm tra hai câu hỏi trung tâm:

> **Context có cải thiện security finding prioritization so với scanner severity hay không?**

và:

> **Machine Learning có tạo thêm giá trị so với một deterministic context-aware scoring method hay không?**

---

# **2\. Core Research Concept**

Security scanner có thể trả lời:

> **“Có security issue nào?”**

Nhưng bài toán nghiên cứu của đề tài là:

> **“Trong các security issues đã phát hiện, issue nào nên được xử lý trước trong context hiện tại?”**

Mô hình tổng quát:

            Terraform Artifact  
                    │  
                    ▼  
             Security Scanner  
                    │  
                    ▼  
            Security Findings  
                    │  
          ┌─────────┴──────────┐  
          │                    │  
          ▼                    ▼  
 Finding Information     Context Information  
          │                    │  
          └─────────┬──────────┘  
                    ▼  
             Feature Vector X  
                    │  
        ┌───────────┼────────────┐  
        ▼           ▼            ▼  
     Severity    Contextual     Machine  
      Only         Rule        Learning  
        │           │            │  
        └───────────┼────────────┘  
                    ▼  
             Priority Scores  
                    │  
                    ▼  
             Finding Rankings  
                    │  
                    ▼  
           Compare with Human  
              Ground Truth  
                    │  
                    ▼  
          Ranking Evaluation  
                    │  
                    ▼  
             Research Result  
---

# **3\. Unit of Analysis**

Đơn vị phân tích chính của nghiên cứu là:

> **Một security finding trong một contextual scenario.**

Không phải toàn bộ Terraform repository và cũng không phải một vulnerability tuyệt đối ngoài thực tế.

Ví dụ:

Scenario: S01-PROD

Terraform:  
AWS infrastructure

Context:  
environment \= production  
asset\_criticality \= high  
data\_sensitivity \= high

Checkov Findings:  
F01  
F02  
F03  
F04  
F05

Khi đó dataset có thể biểu diễn:

| scenario | finding | severity | public | privilege | environment | sensitivity | priority |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| S01 | F01 | High | 1 | 0 | Prod | High | ? |
| S01 | F02 | High | 0 | 1 | Prod | High | ? |
| S01 | F03 | Medium | 0 | 0 | Prod | High | ? |

Dấu `?` chính là target/ground truth mà quá trình annotation cần xác định.

---

# **4\. Conceptual Variables**

Mô hình nghiên cứu gồm bốn nhóm thông tin chính.

## **4.1. Security Finding Characteristics**

Đây là thông tin liên quan trực tiếp đến finding được security scanner phát hiện.

Candidate variables:

scanner\_severity  
check\_id / policy category  
resource\_type  
misconfiguration\_type

Ví dụ:

Finding:  
Publicly accessible storage

Scanner severity:  
HIGH

Resource:  
aws\_s3\_bucket

Scanner information mô tả **finding là gì**, nhưng chưa nhất thiết mô tả đầy đủ mức độ ưu tiên trong deployment context.

---

## **4.2. Infrastructure Security Context**

Nhóm thứ hai mô tả trạng thái hoặc đặc điểm security của resource/infrastructure liên quan đến finding.

Các candidate contextual variables:

internet\_exposure  
privilege\_impact  
reachability  
public\_access  
wildcard\_action  
wildcard\_resource  
encryption\_missing  
logging\_missing

Các feature này phải có evidence từ:

Terraform  
OR  
Scanner Evidence

thay vì được suy đoán chủ quan.

Ví dụ:

Security Group  
0.0.0.0/0  
Port 22

có thể tạo ra contextual information liên quan đến Internet exposure.

---

# **5\. Deployment / Business Context**

Một security issue có thể có mức độ ưu tiên khác nhau tùy vào vai trò của infrastructure.

Các candidate scenario-level variables:

environment  
asset\_criticality  
data\_sensitivity

Ví dụ:

Context A

environment       \= development  
asset\_criticality \= low  
data\_sensitivity  \= low

so với:

Context B

environment       \= production  
asset\_criticality \= high  
data\_sensitivity  \= high

Business context phải được cung cấp thông qua explicit scenario metadata.

Không suy luận business context chỉ từ tên resource.

---

# **6\. Contextual Security Representation**

Ba nhóm thông tin được kết hợp thành contextual representation:

Security Finding  
       \+  
Infrastructure Security Context  
       \+  
Deployment / Business Context  
       ↓  
Contextual Security Representation

Ở mức Machine Learning, representation này trở thành một **feature vector**.

Ký hiệu:

X \= \[x1, x2, x3, ..., xn\]

Trong đó mỗi `x` là một feature.

Ví dụ đơn giản:

X \= \[  
    severity,  
    resource\_type,  
    internet\_exposure,  
    privilege\_impact,  
    reachability,  
    environment,  
    asset\_criticality,  
    data\_sensitivity  
\]

Ví dụ cụ thể:

severity            \= HIGH  
resource\_type       \= S3  
internet\_exposure   \= 1  
privilege\_impact    \= 0  
reachability        \= 1  
environment         \= PROD  
asset\_criticality   \= HIGH  
data\_sensitivity    \= HIGH

Đây là thông tin mà prioritization method sử dụng để đánh giá finding.

---

# **7\. Target Variable / Ground Truth**

Machine Learning cần một target để học.

Ký hiệu:

X → y

Trong đề tài:

X \= finding \+ context features

y \= contextual priority

Ground truth được xây dựng thông qua human security prioritization.

Annotator được cung cấp:

Terraform Evidence  
        \+  
Security Finding  
        \+  
Infrastructure Context  
        \+  
Business Context  
        ↓  
Human Security Judgment  
        ↓  
Priority Ranking

Ví dụ một scenario có năm findings:

Human Ground Truth

Rank 1 → F03  
Rank 2 → F01  
Rank 3 → F05  
Rank 4 → F02  
Rank 5 → F04

Ground truth trong nghiên cứu phải được hiểu là:

> **human-defined contextual security priority under the study methodology**

chứ không phải:

> “absolute real-world cyber risk”.

Nếu chỉ có một annotator, đây phải được công bố là một limitation của nghiên cứu.

---

# **8\. Critical Separation: Ground Truth vs Model**

Một nguyên tắc quan trọng của conceptual framework là:

                    HUMAN  
                       │  
                       ▼  
Finding \+ Evidence \+ Context  
                       │  
                       ▼  
                 Ground Truth  
                       │  
                       │  
                       │ used for  
                       ▼  
                  ML Training  
                       \+  
                  Evaluation

Annotator không được xem:

Random Forest prediction  
Context baseline score  
Final ranking metric  
Model feature importance

trong quá trình tạo ground truth.

Mục đích là hạn chế việc model output ảnh hưởng ngược lại quá trình annotation.

---

# **9\. Circularity Risk**

Đây là một trong những vấn đề quan trọng nhất của mô hình nghiên cứu.

Giả sử ground truth được tạo hoàn toàn bằng công thức:

Production       \+3  
Public            \+3  
Sensitive         \+3  
High Privilege    \+3

sau đó ML nhận chính:

production  
public  
sensitive  
privilege

làm input.

Khi đó:

Rubric  
  ↓  
Ground Truth  
  ↓  
ML learns Ground Truth

nhưng ground truth thực chất lại là:

same features  
  ↓  
fixed formula

Model có thể đạt kết quả rất cao chỉ vì:

> **ML đang học lại công thức tạo label.**

Do đó, conceptual framework không giả định rằng contextual features tự động tạo ra ground truth theo một công thức cố định.

Human annotation nên sử dụng security evidence và predefined assessment principles để đưa ra judgment, đồng thời lưu rationale.

Deterministic contextual scoring được giữ riêng như một **baseline**.

Nhờ vậy nghiên cứu có thể kiểm tra:

Human Judgment  
       ▲  
       │  
 ┌─────┴──────────────┐  
 │                    │  
Context Rule      Machine Learning  
 │                    │  
 └──────── compare ────┘

Nếu Random Forest chỉ tái tạo deterministic scoring thì kết quả nghiên cứu cần phản ánh đúng điều đó thay vì tuyên bố model đã “học real-world risk”.

---

# **10\. Prioritization Methods**

Conceptual framework so sánh ba phương pháp.

## **Method A — Severity-Only Baseline**

Mô hình đơn giản nhất:

Security Finding  
       ↓  
Scanner Severity  
       ↓  
Priority Ranking

Ký hiệu:

Pseverity \= f(severity)

Phương pháp này đại diện cho trường hợp prioritization không sử dụng deployment context.

---

## **Method B — Deterministic Context-Aware Baseline**

Phương pháp thứ hai sử dụng context nhưng không sử dụng ML.

Severity  
   \+  
Infrastructure Context  
   \+  
Business Context  
        ↓  
Predefined Rules  
        ↓  
Context Score  
        ↓  
Ranking

Ký hiệu:

Pcontext \= g(X)

Trong đó `g()` là deterministic scoring function.

Mục đích của baseline này là tách riêng hai câu hỏi:

Context có giá trị không?

và:

Có thật sự cần ML không?  
---

## **Method C — ML Context-Aware Prioritization**

Phương pháp nghiên cứu chính:

Feature Vector X  
       ↓  
Random Forest  
       ↓  
Priority Score  
       ↓  
Sort  
       ↓  
Predicted Ranking

Ký hiệu:

PML \= ML(X)

Random Forest không trực tiếp “hiểu security”.

Nó học statistical patterns giữa:

features X

và:

human priority y

từ training data.

---

# **11\. Main Comparative Research Model**

Toàn bộ experiment chính có thể mô tả bằng:

                    SECURITY FINDINGS  
                            │  
               ┌────────────┴────────────┐  
               │                         │  
               ▼                         ▼  
        Scanner Information          Context  
               │                         │  
               └────────────┬────────────┘  
                            ▼  
                    Feature Dataset  
                            │  
          ┌─────────────────┼─────────────────┐  
          │                 │                 │  
          ▼                 ▼                 ▼  
     SEVERITY           CONTEXTUAL        RANDOM  
      ONLY                RULE            FOREST  
          │                 │                 │  
          ▼                 ▼                 ▼  
      Ranking A         Ranking B         Ranking C  
          │                 │                 │  
          └─────────────────┼─────────────────┘  
                            ▼  
                    HUMAN RANKING  
                      Ground Truth  
                            │  
                            ▼  
                 Ranking Performance  
                            │  
               ┌────────────┼─────────────┐  
               ▼            ▼             ▼  
             NDCG@3       NDCG@5       Spearman  
---

# **12\. Research Questions Mapping**

Conceptual framework hỗ trợ bốn Research Questions.

## **RQ1 — Contextual Factors**

> **Which contextual factors are useful for determining the priority of security findings in Terraform infrastructure?**

Phân tích thông qua:

Feature Importance  
\+  
Ablation  
\+  
Contrastive Analysis

RQ1 mang tính exploratory.

Không diễn giải feature importance đơn giản thành causal importance.

---

## **RQ2 — Value of Context**

> **Does incorporating deployment context improve security finding prioritization compared with scanner severity alone?**

So sánh chính:

Severity Baseline  
        VS  
Contextual Baseline

Nếu contextual baseline tốt hơn:

Contextual \> Severity

thì nghiên cứu có evidence cho thấy context có ích trong benchmark được nghiên cứu.

Không tự động suy rộng kết quả ra toàn bộ cloud security.

---

## **RQ3 — Value of Machine Learning**

> **Can a Machine Learning-based prioritization approach provide better ranking performance than deterministic context-based scoring?**

So sánh:

Contextual Rule  
       VS  
Random Forest

Có ba kết quả đều hợp lệ:

RF \> Rule

RF ≈ Rule

RF \< Rule

Nếu:

RF ≈ Rule

thì một kết luận có thể là:

> Trong phạm vi benchmark được nghiên cứu, chưa có đủ bằng chứng cho thấy ML tạo ra lợi ích đáng kể so với deterministic contextual scoring.

Đây vẫn là một research result hợp lệ.

---

## **RQ4 — Model Interpretation**

> **Which contextual factors contribute most to the prioritization behavior of the ML model?**

Phân tích bằng:

Feature Importance  
Permutation Importance  
Minimal Ablation

RQ4 nhằm giải thích model behavior.

Không được diễn giải:

feature importance

thành:

real-world causal security risk

mà không có bằng chứng bổ sung.

---

# **13\. Research Hypotheses**

Nếu luận văn yêu cầu hypotheses, có thể sử dụng:

### **H1 — Context Hypothesis**

> Context-aware prioritization achieves different ranking performance from severity-only prioritization on the defined benchmark.

Không nên viết trước:

> “Context chắc chắn tốt hơn.”

Kết quả thực nghiệm quyết định direction.

### **H2 — Machine Learning Hypothesis**

> Machine Learning-based contextual prioritization achieves different ranking performance from deterministic context-aware scoring on the defined benchmark.

Tương tự, nghiên cứu không giả định ML phải thắng.

---

# **14\. Training Concept**

Với người mới học ML, quá trình training có thể hiểu đơn giản:

Historical / Annotated Examples  
              │  
              ▼  
     ┌─────────────────┐  
     │ Finding Features│  
     │        X        │  
     └────────┬────────┘  
              │  
              │ together with  
              ▼  
     ┌─────────────────┐  
     │ Human Priority  │  
     │        y        │  
     └────────┬────────┘  
              │  
              ▼  
       Random Forest  
              │  
              ▼  
         Learned Model

Ví dụ:

Finding A

severity          \= HIGH  
public            \= YES  
environment       \= PROD  
sensitive         \= HIGH  
privilege\_impact  \= LOW

Human priority    \= 0.92

Model nhìn nhiều ví dụ tương tự và học:

X → y

Đây được gọi là **supervised learning**.

---

# **15\. Inference Concept**

Sau khi model được train, model có thể nhận finding mới:

NEW TERRAFORM  
      │  
      ▼  
   CHECKOV  
      │  
      ▼  
NEW SECURITY FINDINGS  
      │  
      ▼  
CONTEXT EXTRACTION  
      │  
      ▼  
FEATURE VECTOR Xnew  
      │  
      ▼  
TRAINED RANDOM FOREST  
      │  
      ▼  
PRIORITY SCORE  
      │  
      ▼  
SORT FINDINGS  
      │  
      ▼  
PRIORITIZED FINDINGS

Điểm quan trọng:

> **Ground truth không tồn tại trong inference pipeline.**

Ground truth chỉ cần cho:

training  
\+  
validation  
\+  
research evaluation  
---

# **16\. Training vs Operational Workflow**

Hai quá trình cần được phân biệt.

## **Research / Training**

Terraform  
   ↓  
Checkov  
   ↓  
Findings  
   ↓  
Context  
   ↓  
Human Annotation  
   ↓  
Dataset X \+ y  
   ↓  
Train Model  
   ↓  
Evaluate Model

## **Operational / Prototype**

New Terraform  
   ↓  
Checkov  
   ↓  
Findings  
   ↓  
Context  
   ↓  
Trained Model  
   ↓  
Priority Score  
   ↓  
Ranking  
   ↓  
Security Gate

Đây là điểm quan trọng khi sau này thiết kế System Architecture.

---

# **17\. Evaluation Model**

Model không được đánh giá chủ yếu bằng câu hỏi:

> “Priority score dự đoán có chính xác tuyệt đối không?”

Bài toán chính là:

> **Model có đưa đúng findings quan trọng lên đầu danh sách không?**

Do đó:

Predicted Ranking  
        │  
        │ compare  
        ▼  
Human Ground-Truth Ranking  
        │  
        ▼  
Ranking Metrics

Candidate metrics:

NDCG@3  
NDCG@5  
Spearman Rank Correlation

NDCG@K đặc biệt hữu ích vì nghiên cứu quan tâm đến các findings nằm gần đầu danh sách remediation.

---

# **18\. Contrastive Context Model**

Secondary experiment có thể sử dụng cùng infrastructure nhưng thay đổi context.

                  SAME TERRAFORM  
                        │  
             ┌──────────┴──────────┐  
             ▼                     ▼  
         CONTEXT A             CONTEXT B

       Development             Production  
       Low Criticality         High Criticality  
       Low Sensitivity         High Sensitivity  
             │                     │  
             ▼                     ▼  
        Feature XA            Feature XB  
             │                     │  
             └──────────┬──────────┘  
                        ▼  
                       ML  
             ┌──────────┴──────────┐  
             ▼                     ▼  
          Score A               Score B

Sau đó phân tích:

Δscore \= ScoreB \- ScoreA

Câu hỏi ở đây là:

> Khi infrastructure giữ nguyên nhưng security-relevant context thay đổi, prioritization method có phản ứng theo hướng hợp lý hay không?

Contrastive analysis là secondary evidence, không thay thế main benchmark evaluation.

---

# **19\. Data Leakage Boundary**

Conceptual framework phải bảo đảm:

TRAINING FAMILY  
      │  
      X  
      │  
TEST FAMILY

không chia các scenario gần như giống nhau của cùng một family sang cả train và test.

Ví dụ:

Family F01  
├── F01-DEV  
└── F01-PROD

phải cùng nằm trong một data partition.

Do đó:

Dataset  
   ↓  
Group by Family  
   ↓  
Train / Validation / Test

thay vì:

Individual Findings  
   ↓  
Random Split

Mục tiêu là hạn chế model nhìn thấy gần như cùng một infrastructure trong quá trình training và testing.

---

# **20\. Conceptual Threats to Validity**

Mô hình nghiên cứu có một số limitations cần được thừa nhận ngay từ thiết kế.

### **Ground-Truth Subjectivity**

Human priority là judgment và có thể khác giữa các security practitioners.

### **Single-Annotator Bias**

Nếu chỉ có một annotator, ground truth có thể phản ánh quan điểm của người đó.

### **Context–Label Circularity**

Nếu label được tạo bằng đúng một deterministic formula từ các features, ML có thể chỉ học lại formula đó.

### **Scanner Dependency**

Finding population phụ thuộc vào Checkov policies và version được sử dụng.

### **Dataset Bias**

AI-generated Terraform artifacts hoặc benchmark được chọn có thể không đại diện cho Terraform ngoài thực tế.

### **Finding Dependency**

Nhiều scanner findings có thể xuất phát từ cùng một underlying configuration issue.

### **Limited Generalization**

Kết quả trên:

AWS \+ Terraform \+ Checkov

không tự động chứng minh kết quả tương tự trên:

Azure  
GCP  
CloudFormation  
Kubernetes  
other scanners  
---

# **21\. What the Study Can Claim**

Nếu experiment thành công, nghiên cứu có thể đưa ra claim ở mức:

> **Trong benchmark AWS Terraform và contextual representation được định nghĩa trong nghiên cứu, việc bổ sung context tạo ra sự khác biệt về chất lượng security finding prioritization so với severity-only baseline.**

Nếu Random Forest tốt hơn contextual baseline với evidence phù hợp:

> **Trong experimental setting được nghiên cứu, ML-based contextual prioritization đạt ranking performance tốt hơn deterministic contextual scoring.**

Không nên claim:

> “Machine Learning xác định chính xác real-world cyber risk.”

hoặc:

> “Model có thể thay thế security analyst.”

---

# **22\. Final Conceptual Framework**

Mô hình nghiên cứu cuối cùng có thể tóm tắt bằng:

┌─────────────────────────────────────────────────────────┐  
│                    INPUT DOMAIN                         │  
│                                                         │  
│             AI-Generated Terraform                     │  
└───────────────────────────┬─────────────────────────────┘  
                            │  
                            ▼  
┌─────────────────────────────────────────────────────────┐  
│                 SECURITY ANALYSIS                       │  
│                                                         │  
│                       Checkov                           │  
│                          │                              │  
│                          ▼                              │  
│                  Security Findings                     │  
└───────────────────────────┬─────────────────────────────┘  
                            │  
              ┌─────────────┼──────────────┐  
              ▼             ▼              ▼  
        Finding Info   Infrastructure   Business /  
                         Context        Deployment  
                                         Context  
              │             │              │  
              └─────────────┼──────────────┘  
                            ▼  
┌─────────────────────────────────────────────────────────┐  
│              CONTEXTUAL REPRESENTATION                  │  
│                                                         │  
│                   Feature Vector X                      │  
└───────────────────────────┬─────────────────────────────┘  
                            │  
          ┌─────────────────┼─────────────────┐  
          ▼                 ▼                 ▼  
┌────────────────┐ ┌────────────────┐ ┌──────────────────┐  
│ Severity-Only  │ │ Context Rule   │ │ Random Forest    │  
│ Baseline       │ │ Baseline       │ │ ML Model         │  
└───────┬────────┘ └───────┬────────┘ └────────┬─────────┘  
        │                  │                   │  
        ▼                  ▼                   ▼  
   Ranking A          Ranking B           Ranking C  
        │                  │                   │  
        └──────────────────┼───────────────────┘  
                           │  
                           ▼  
                 ┌──────────────────┐  
                 │ Human Priority   │  
                 │ Ground Truth     │  
                 └────────┬─────────┘  
                          │  
                          ▼  
┌─────────────────────────────────────────────────────────┐  
│                   EVALUATION                            │  
│                                                         │  
│          NDCG@3 • NDCG@5 • Spearman                    │  
│                                                         │  
│ Severity vs Context Rule vs Random Forest               │  
└───────────────────────────┬─────────────────────────────┘  
                            │  
                            ▼  
┌─────────────────────────────────────────────────────────┐  
│                RESEARCH CONCLUSIONS                     │  
│                                                         │  
│ RQ1: Which context factors matter?                      │  
│ RQ2: Does context improve prioritization?               │  
│ RQ3: Does ML add value beyond deterministic rules?      │  
│ RQ4: How does the model use contextual information?     │  
└─────────────────────────────────────────────────────────┘  
---

# **23\. Simplified Mental Model**

Để hiểu toàn bộ framework ở mức đơn giản nhất:

CHECKOV  
"Em có những lỗi gì?"  
        │  
        ▼  
CONTEXT  
"Những lỗi này đang nằm trong hoàn cảnh nào?"  
        │  
        ▼  
HUMAN GROUND TRUTH  
"Theo security judgment, lỗi nào nên sửa trước?"  
        │  
        ▼  
ML  
"Học từ các ví dụ đó."  
        │  
        ▼  
NEW FINDING  
"Dựa trên những gì đã học,  
finding này nên được ưu tiên bao nhiêu?"  
        │  
        ▼  
EVALUATION  
"ML xếp có giống human không,  
và có tốt hơn cách đơn giản hơn không?"

Có thể tóm tắt conceptual framework bằng một câu:

> **Security scanner identifies findings; contextual information describes their security situation; human judgment defines the study target; prioritization methods estimate relative priority; and empirical evaluation determines whether context and Machine Learning provide measurable value over simpler baselines.**

# System Architecture — Kiến trúc hệ thống.

# **SYSTEM ARCHITECTURE — KIẾN TRÚC HỆ THỐNG**

## **1\. Mục đích của kiến trúc hệ thống**

Kiến trúc hệ thống được thiết kế nhằm hỗ trợ quá trình nghiên cứu **Context-Aware Machine Learning for Security Risk Prioritization of Generative-AI-Generated Terraform**.

Mục tiêu của hệ thống không phải là xây dựng một công cụ phát hiện lỗ hổng bảo mật mới. Thay vào đó, hệ thống sử dụng kết quả từ công cụ phân tích tĩnh hiện có, cụ thể là **Checkov**, sau đó bổ sung thông tin ngữ cảnh và áp dụng các phương pháp ưu tiên khác nhau để xác định những phát hiện bảo mật nào nên được xử lý trước.

Kiến trúc vì vậy tập trung vào chuỗi xử lý:

**Terraform → Static Security Findings → Context → Features → Priority Model → Ranked Findings → Security Gate**

Generative AI chỉ đóng vai trò là **nguồn tạo ra các Terraform artifacts được nghiên cứu**, không phải thành phần chạy trong hệ thống. Thành phần AI/ML chính của kiến trúc là mô hình **Random Forest** dùng để học cách ưu tiên các security findings dựa trên ngữ cảnh. Điều này phù hợp với phạm vi nghiên cứu đã được giới hạn ở AWS, Terraform, Checkov, static analysis và Random Forest.

---

## **2\. Nguyên tắc thiết kế kiến trúc**

Kiến trúc được xây dựng theo các nguyên tắc chính sau:

1. **Đơn giản và có thể triển khai bởi một sinh viên.**  
   Hệ thống ưu tiên các module Python độc lập thay vì microservices hoặc kiến trúc phân tán.  
2. **Tách detection khỏi prioritization.**  
   Checkov chịu trách nhiệm phát hiện security misconfigurations; hệ thống nghiên cứu chịu trách nhiệm ưu tiên các findings đó.  
3. **Tách dữ liệu khách quan khỏi dữ liệu ngữ cảnh.**  
   Thông tin như `environment`, `asset_criticality` và `data_sensitivity` là scenario/business context; trong khi các đặc điểm như `internet_exposure`, `privilege_impact` hoặc các đặc điểm cấu hình hạ tầng được trích xuất từ Terraform/finding.  
4. **Tách training khỏi inference.**  
   Human annotation chỉ được sử dụng trong quá trình xây dựng benchmark và huấn luyện/đánh giá. Khi prototype hoạt động, hệ thống không yêu cầu người dùng cung cấp priority rank.  
5. **Ngăn data leakage và circularity.**  
   Các feature phải được xác định trước annotation và việc chia train/test phải dựa trên `family_id`, không chia ngẫu nhiên từng finding.  
6. **Không giả định Machine Learning luôn tốt hơn rule-based approach.**  
   Severity-only baseline, deterministic contextual baseline và Random Forest đều phải được đánh giá thực nghiệm.

---

# **3\. Kiến trúc tổng thể**

Kiến trúc tổng thể có thể biểu diễn như sau:

┌─────────────────────────────────────────────┐  
│           SOURCE / ARTIFACT LAYER           │  
│                                             │  
│  GenAI-generated / Published Terraform      │  
│  \+ provenance / family\_id / scenario\_id     │  
└──────────────────────┬──────────────────────┘  
                       │  
                       ▼  
┌─────────────────────────────────────────────┐  
│        TERRAFORM VALIDATION LAYER           │  
│                                             │  
│        terraform fmt / validate             │  
└──────────────────────┬──────────────────────┘  
                       │  
                       ▼  
┌─────────────────────────────────────────────┐  
│        STATIC SECURITY ANALYSIS             │  
│                                             │  
│                  Checkov                    │  
│                       │                     │  
│                       ▼                     │  
│              Raw JSON Findings              │  
└──────────────────────┬──────────────────────┘  
                       │  
                       ▼  
┌─────────────────────────────────────────────┐  
│             FINDING NORMALIZER              │  
│                                             │  
│ Raw Checkov JSON → Normalized Findings      │  
└──────────────────────┬──────────────────────┘  
                       │  
            ┌──────────┴───────────┐  
            │                      │  
            ▼                      ▼  
┌─────────────────────┐   ┌──────────────────────┐  
│  CONTEXT MANAGER    │   │ INFRASTRUCTURE       │  
│                     │   │ FEATURE EXTRACTOR    │  
│ environment         │   │                      │  
│ asset criticality   │   │ internet exposure    │  
│ data sensitivity    │   │ privilege impact     │  
└──────────┬──────────┘   │ resource properties  │  
           │              └──────────┬───────────┘  
           │                         │  
           └────────────┬────────────┘  
                        ▼  
              ┌──────────────────┐  
              │ FEATURE BUILDER  │  
              │                  │  
              │ ML-ready dataset │  
              └────────┬─────────┘  
                       │  
          ┌────────────┴───────────────┐  
          │                            │  
          ▼                            ▼  
┌───────────────────────┐   ┌───────────────────────┐  
│ GROUND TRUTH /        │   │ BASELINE / ML         │  
│ HUMAN ANNOTATION      │   │ MODELS                │  
│                       │   │                       │  
│ Human priority rank   │   │ Severity Baseline     │  
│ Rank → relevance      │   │ Contextual Baseline   │  
└──────────┬────────────┘   │ Random Forest         │  
           │                └──────────┬────────────┘  
           └─────────────┬─────────────┘  
                         ▼  
               ┌───────────────────┐  
               │ EVALUATION ENGINE │  
               │                   │  
               │ NDCG@3 / NDCG@5  │  
               │ Spearman          │  
               │ Statistical tests │  
               └─────────┬─────────┘  
                         │  
                         ▼  
               ┌───────────────────┐  
               │ TRAINED MODEL /   │  
               │ RESEARCH RESULTS  │  
               └─────────┬─────────┘  
                         │  
                         ▼  
              ┌────────────────────┐  
              │ OPERATIONAL        │  
              │ PRIORITIZATION     │  
              │                    │  
              │ Priority Score     │  
              │ Ranking            │  
              │ PASS/REVIEW/BLOCK  │  
              └────────────────────┘

Kiến trúc này cố ý giữ hệ thống dưới dạng **modular research pipeline**, thay vì phát triển thành một nền tảng DevSecOps hoàn chỉnh.

---

# **4\. Các thành phần chính**

## **4.1. Source / Artifact Layer**

Đây là tầng đầu vào của hệ thống.

Dữ liệu chính là các Terraform artifacts có nguồn gốc rõ ràng, ưu tiên tái sử dụng các artifact hoặc benchmark từ nghiên cứu trước thay vì tự tạo toàn bộ dataset từ đầu.

Theo Research Protocol v2.3, dữ liệu được tổ chức theo ba mức:

**Tier 1 — Source Corpus**

Tập artifact ban đầu thu thập từ các nguồn nghiên cứu có provenance và điều kiện sử dụng phù hợp.

**Tier 2 — Research Corpus**

Các artifact được chọn sau khi thỏa mãn các điều kiện nghiên cứu như AWS, Terraform, có thể validate/scan và có security findings.

**Tier 3 — Prioritization Benchmark**

Tập con được lựa chọn để thực hiện human annotation và các thí nghiệm prioritization.

Một artifact nên được gắn các identifier tối thiểu như:

source\_id  
family\_id  
scenario\_id  
terraform\_path  
source/provenance

Trong đó `family_id` đặc biệt quan trọng vì được sử dụng để ngăn các Terraform gần giống nhau xuất hiện đồng thời trong train và test.

---

# **5\. Terraform Validation Layer**

Trước khi thực hiện security scanning, Terraform artifact phải được kiểm tra về khả năng xử lý cú pháp và cấu hình.

Pipeline cơ bản:

Terraform Artifact  
        │  
        ▼  
terraform fmt  
        │  
        ▼  
terraform validate  
        │  
   ┌────┴─────┐  
   │          │  
 Valid      Invalid  
   │          │  
   ▼          ▼  
Checkov    Error Log

Artifact không thể validate phải được ghi nhận rõ trạng thái thay vì âm thầm loại bỏ.

Việc validate và scan là một phần của workflow nghiên cứu đã được xác định, trong đó Checkov được sử dụng với phiên bản được pin để tăng reproducibility.

---

# **6\. Static Security Analysis Layer**

Sau validation, Terraform được đưa vào **Checkov** để thực hiện static security analysis.

Checkov chịu trách nhiệm trả lời:

> **“Terraform này có những security misconfiguration nào?”**

Ví dụ một raw finding có thể chứa:

check\_id  
check\_name  
resource  
resource\_type  
file\_path  
line\_range  
check\_result

Checkov không phải là mô hình ML của nghiên cứu và cũng không phải contribution chính của đề tài.

Vai trò của Checkov là cung cấp tập security findings ban đầu để hệ thống prioritization xử lý.

---

# **7\. Finding Normalizer**

Kết quả Checkov JSON không được đưa trực tiếp vào ML.

Một **Finding Normalizer** được sử dụng để chuyển output của scanner thành schema thống nhất.

Ví dụ:

finding\_id  
scenario\_id  
family\_id

check\_id  
check\_name

resource\_address  
resource\_type

file\_path  
start\_line  
end\_line

scanner\_severity

Normalizer giúp tách phần phụ thuộc vào Checkov khỏi phần còn lại của pipeline.

Điều này cũng cho phép các bước Feature Engineering, Annotation và Evaluation làm việc với cùng một cấu trúc dữ liệu. Workflow hiện tại đã xác định một bước normalization riêng cho các trường finding trước khi annotation và modeling.

Một vấn đề cần lưu ý là trong pilot, Checkov có thể trả về `severity=None`. Vì vậy, severity-only baseline cần một severity mapping/policy riêng và policy này phải được freeze trước evaluation.

---

# **8\. Context Manager**

Context Manager quản lý các thông tin mô tả hoàn cảnh triển khai mà scanner thông thường không biết.

Ba contextual variables cốt lõi gồm:

environment  
asset\_criticality  
data\_sensitivity

Ví dụ:

{  
  "environment": "production",  
  "asset\_criticality": "high",  
  "data\_sensitivity": "high"  
}

Một scenario khác của cùng Terraform family có thể có:

{  
  "environment": "development",  
  "asset\_criticality": "low",  
  "data\_sensitivity": "low"  
}

Thiết kế này cho phép nghiên cứu kiểm tra liệu cùng một technical finding có nên được ưu tiên khác nhau khi business/deployment context thay đổi hay không.

Context A/B trong protocol được thiết kế theo nguyên tắc Terraform giống hoặc tương đương trong khi contextual metadata thay đổi. Tuy nhiên, tài liệu cũng nhấn mạnh rằng thay đổi context **không bắt buộc** human ranking phải thay đổi; ranking vẫn phải dựa trên rationale của người đánh giá.

---

# **9\. Infrastructure Feature Extractor**

Khác với Context Manager, component này trích xuất các đặc điểm có thể quan sát khách quan từ Terraform và security finding.

Các feature có thể bao gồm:

internet\_exposure  
privilege\_impact  
reachability  
public\_access  
wildcard\_action  
wildcard\_resource  
encryption\_missing  
logging\_missing

Chỉ những feature có thể suy ra một cách khách quan và reproducible mới nên được sử dụng.

Ví dụ:

0.0.0.0/0  
      ↓  
internet\_exposure \= 1

Không nên suy luận:

resource\_name \= "important\_database"

→ asset\_criticality \= HIGH

vì tên resource không phải bằng chứng khách quan về business criticality.

Protocol phân biệt các scenario/business features với finding/resource-level features và yêu cầu các finding-level features phải được xác định trước quá trình annotation.

---

# **10\. Feature Builder**

Feature Builder kết hợp ba nhóm thông tin:

Normalized Finding  
        \+  
Scenario Context  
        \+  
Infrastructure Features  
        ↓  
ML Feature Vector

Một record có thể có dạng khái niệm:

finding\_id  
family\_id  
scenario\_id

environment  
asset\_criticality  
data\_sensitivity

internet\_exposure  
privilege\_impact  
reachability

resource\_type  
scanner\_severity

Các categorical features sau đó có thể được encode để Random Forest xử lý.

Điểm quan trọng là:

> **Feature Builder không được sử dụng human priority rank để tạo feature.**

Nếu feature được tạo sau khi nhìn vào ground truth, hệ thống có nguy cơ xảy ra target leakage hoặc circularity.

---

# **11\. Ground Truth / Human Annotation Component**

Đây là thành phần nghiên cứu dùng để tạo ra câu trả lời tham chiếu cho bài toán prioritization.

Human annotator xem xét các findings trong cùng một scenario và xếp hạng:

Rank 1 → cần xử lý trước nhất  
Rank 2 → ưu tiên tiếp theo  
Rank 3 → ưu tiên tiếp theo  
...

Mỗi finding trong cùng scenario phải có một rank duy nhất theo protocol hiện tại.

Sau đó rank có thể được ánh xạ sang relevance grade để đánh giá ranking:

Rank 1 → relevance 3  
Rank 2 → relevance 2  
Rank 3 → relevance 1  
Rank 4+ → relevance 0

Đây là mapping đã được xác định cho NDCG.

Human annotation chỉ tồn tại trong:

Research / Training / Evaluation Path

và **không nằm trong operational inference path**.

Một giới hạn cần được ghi rõ trong luận văn là ground truth ở đây thực chất là **study-defined contextual priority**, phụ thuộc vào annotation rubric và người đánh giá; nó không nên được trình bày như một “security truth” tuyệt đối.

---

# **12\. Dataset Builder**

Dataset Builder kết hợp:

Normalized Findings  
\+  
Context Features  
\+  
Infrastructure Features  
\+  
Human Ground Truth

để tạo dataset dùng cho experiment.

Một schema đơn giản có thể là:

family\_id  
scenario\_id  
finding\_id

scanner\_severity

environment  
asset\_criticality  
data\_sensitivity

internet\_exposure  
privilege\_impact  
reachability

resource\_type

human\_rank  
relevance\_grade

Dataset không được chia train/test ngẫu nhiên theo từng finding.

Thay vào đó:

Family A ─┐  
Family B  ├── TRAIN  
Family C ─┘

Family D ─┐  
Family E  ├── TEST  
Family F ─┘

hoặc sử dụng GroupKFold/Leave-One-Family-Out theo `family_id`.

Mục tiêu là tránh trường hợp những variants gần giống nhau của cùng Terraform family xuất hiện ở cả train và test. Đây là nguyên tắc split đã được protocol xác định rõ.

---

# **13\. Prioritization Models**

Kiến trúc bao gồm ba phương pháp chính để trả lời câu hỏi nghiên cứu.

## **13.1. Severity-Only Baseline**

Baseline đơn giản nhất:

Scanner Finding  
      ↓  
Severity  
      ↓  
Priority Ranking

Baseline này đại diện cho cách ưu tiên chỉ dựa vào mức severity của scanner.

Nó được sử dụng để kiểm tra liệu bổ sung contextual information có mang lại lợi ích hay không.

---

## **13.2. Deterministic Contextual Baseline**

Baseline thứ hai sử dụng context nhưng không sử dụng Machine Learning.

Khái niệm:

Priority \=  
    Severity contribution  
  \+ Environment contribution  
  \+ Criticality contribution  
  \+ Data sensitivity contribution  
  \+ Exposure contribution  
  \+ Privilege contribution

Trọng số và công thức phải được xác định trước khi xem kết quả cuối cùng của ML.

Mục đích của baseline này là trả lời câu hỏi quan trọng:

> Nếu context có ích, liệu chỉ cần một rule-based scoring đơn giản đã đủ hay ML thực sự mang lại giá trị bổ sung?

Đây là một đối chứng quan trọng trong thiết kế nghiên cứu.

---

# **14\. Random Forest Model**

Random Forest là mô hình Machine Learning chính.

Pipeline huấn luyện:

Feature Dataset  
      ↓  
Family-based Split  
      ↓  
Preprocessing  
      ↓  
RandomForestRegressor  
      ↓  
Training  
      ↓  
Trained Model

Model nhận contextual/security features làm input và tạo ra một **continuous priority score**.

Ví dụ:

Finding A → 0.91  
Finding B → 0.76  
Finding C → 0.34  
Finding D → 0.18

Sau đó:

sort(priority\_score, descending=True)

tạo ranking:

1\. Finding A  
2\. Finding B  
3\. Finding C  
4\. Finding D

Do đó, output chính của hệ thống là **ranking**, không phải classification kiểu “vulnerability / non-vulnerability”.

Random Forest được chọn làm model chính trong thiết kế nghiên cứu; XGBoost chỉ là extension tùy chọn.

---

# **15\. Evaluation Engine**

Evaluation Engine so sánh ba phương pháp:

Severity Only  
      vs  
Contextual Rule  
      vs  
Random Forest

Metric chính là:

NDCG@3  
NDCG@5

Metric phụ:

Spearman Rank Correlation

Các metric như MAE hoặc RMSE có thể được sử dụng như diagnostic metrics nhưng không phải metric chính, vì mục tiêu nghiên cứu là **ranking quality**, không đơn thuần là numerical prediction accuracy.

Nếu số lượng scenario/family phù hợp, phân tích thống kê có thể bao gồm:

Paired scenario-level comparison  
Wilcoxon signed-rank test  
Effect size  
Bootstrap 95% confidence interval

Các kiểm định này được dùng để đánh giá mức độ ổn định của khác biệt giữa các phương pháp, thay vì chỉ báo cáo một giá trị NDCG trung bình.

---

# **16\. Tách Research Architecture và Operational Architecture**

Một điểm quan trọng là phải phân biệt hai đường xử lý.

## **16.1. Research / Training Path**

Terraform  
   ↓  
Validation  
   ↓  
Checkov  
   ↓  
Normalization  
   ↓  
Context \+ Feature Extraction  
   ↓  
Human Annotation  
   ↓  
Dataset Builder  
   ↓  
Family-based Split  
   ↓  
Baseline \+ Random Forest  
   ↓  
Evaluation  
   ↓  
Research Results

Đây là pipeline phục vụ luận văn.

---

## **16.2. Operational / Inference Path**

Sau khi model đã được huấn luyện:

New Terraform  
     ↓  
Terraform Validation  
     ↓  
Checkov  
     ↓  
Finding Normalizer  
     ↓  
Context Manager  
     ↓  
Feature Builder  
     ↓  
Trained Random Forest  
     ↓  
Priority Score  
     ↓  
Ranked Findings  
     ↓  
Security Gate

Trong operational path:

**không có human\_rank, relevance\_grade hoặc annotation data.**

Điều này ngăn việc vô tình đưa ground truth vào quá trình inference.

---

# **17\. Security Gate**

Security Gate là prototype cuối của hệ thống.

Nó nhận:

Ranked Findings  
\+  
Priority Scores

và áp dụng operational policy để tạo kết quả:

PASS  
REVIEW  
BLOCK

Ví dụ output dạng JSON:

{  
  "decision": "REVIEW",  
  "top\_findings": \[  
    {  
      "finding\_id": "F001",  
      "priority\_score": 0.91,  
      "rank": 1  
    },  
    {  
      "finding\_id": "F004",  
      "priority\_score": 0.76,  
      "rank": 2  
    }  
  \]  
}

Security Gate chỉ là **lightweight prototype** nhằm chứng minh rằng kết quả nghiên cứu có thể được đưa vào một DevSecOps workflow.

Nó không phải một production security enforcement platform.

CLI và JSON output là đủ cho phạm vi luận văn; GitHub Actions có thể được thêm như integration tùy chọn.

---

# **18\. Model và Artifact Storage**

Đề tài không cần database server.

Có thể lưu trữ đơn giản:

data/  
models/  
results/

Ví dụ:

data/  
 ├── raw/  
 ├── normalized/  
 ├── features/  
 └── annotations/

models/  
 └── random\_forest.pkl

results/  
 ├── metrics.csv  
 ├── rankings.csv  
 └── statistical\_results.json

Cách tiếp cận file-based phù hợp hơn với research prototype và giúp tăng reproducibility.

---

# **19\. Error và Failure Handling**

Các bước xử lý lỗi nên được tách rõ để một lỗi ở một stage không làm mất khả năng truy vết toàn bộ pipeline.

Ví dụ:

Terraform syntax error  
        ↓  
validation\_status \= FAILED  
        ↓  
Không scan  
        ↓  
Ghi error log  
Checkov execution error  
        ↓  
scan\_status \= FAILED  
        ↓  
Ghi command/version/error  
Feature không xác định chắc chắn  
        ↓  
UNKNOWN / missing

thay vì tự suy đoán giá trị.

Scenario không đủ findings cho NDCG@5  
        ↓  
Không dùng cho NDCG@5  
        ↓  
Vẫn có thể dùng cho NDCG@3 hoặc phân tích khác

Protocol hiện tại cũng xác định nguyên tắc failure handling và yêu cầu không thay đổi dữ liệu/phương pháp chỉ để tạo ra kết quả hỗ trợ giả thuyết.

---

# **20\. Security và Trust Boundaries**

Hệ thống có ba trust boundary quan trọng.

### **Boundary 1 — External Artifact → Research Dataset**

Terraform lấy từ external/public sources không được mặc định là dữ liệu sạch.

Cần lưu:

source  
provenance  
license  
family\_id  
original artifact

### **Boundary 2 — Scanner → Research Pipeline**

Checkov output được xem là **scanner observation**, không phải ground truth priority.

Điều này giúp tránh suy luận:

Checkov finding \= actual business risk

### **Boundary 3 — Human Annotation → ML**

Human annotation chỉ được dùng làm target/evaluation reference.

Feature extraction phải được hoàn thành trước annotation để giảm nguy cơ người nghiên cứu vô tình encode đáp án vào feature.

---

# **21\. Reproducibility**

Để thí nghiệm có thể tái tạo, hệ thống cần lưu ít nhất:

Terraform version  
Checkov version  
Python version  
Python dependencies  
Random seed  
Dataset version  
Feature schema version  
Annotation version  
Model parameters  
Split information  
Experiment results

Đặc biệt, Checkov phải được pin version thay vì sử dụng phiên bản mới nhất một cách tự động.

Workflow hiện tại sử dụng Checkov `3.3.17`.

Thiết kế reproducibility và repository cũng đã được xem là một phần của blueprint nghiên cứu.

---

# **22\. Cấu trúc source code đề xuất**

Để tránh over-engineering, repository có thể giữ ở mức:

project/  
│  
├── data/  
│   ├── raw/  
│   ├── normalized/  
│   ├── features/  
│   └── annotations/  
│  
├── src/  
│   ├── validate.py  
│   ├── scan.py  
│   ├── normalize.py  
│   ├── context.py  
│   ├── features.py  
│   ├── dataset.py  
│   ├── baselines.py  
│   ├── train.py  
│   ├── evaluate.py  
│   └── gate.py  
│  
├── models/  
│  
├── experiments/  
│  
├── results/  
│  
├── tests/  
│  
├── requirements.txt  
└── README.md

Không cần xây dựng nhiều service hoặc API riêng biệt.

Mỗi Python module tương ứng với một bước logic trong research pipeline, giúp dễ debug và dễ trình bày trong luận văn.

---

# **23\. MVP Architecture**

Phiên bản tối thiểu cần hoàn thành cho luận văn là:

Terraform Dataset  
       ↓  
Terraform Validation  
       ↓  
Checkov  
       ↓  
Finding Normalization  
       ↓  
Context \+ Feature Extraction  
       ↓  
Human Ground Truth  
       ↓  
Dataset Builder  
       ↓  
┌──────────────────────────────┐  
│ Severity Baseline            │  
│ Contextual Baseline          │  
│ Random Forest                │  
└──────────────────────────────┘  
       ↓  
NDCG / Spearman Evaluation  
       ↓  
Priority Ranking  
       ↓  
CLI Security Gate

Đây nên được xem là **kiến trúc bắt buộc**.

---

# **24\. Optional Extensions**

Sau khi MVP hoàn thành, có thể bổ sung:

XGBoost  
Contrastive A/B analysis  
Feature importance  
Feature ablation  
GitHub Actions integration  
Additional visualizations  
Second-annotator subset

Các extension này không nên trở thành dependency bắt buộc để hoàn thành luận văn.

Đặc biệt, XGBoost được xác định là optional trong workflow hiện tại.

---

# **25\. Các thành phần không nên xây dựng**

Để giữ phạm vi phù hợp với một luận văn sinh viên, kiến trúc **không nên mở rộng** sang:

Web dashboard phức tạp  
Microservices  
Kubernetes  
Production database  
Real AWS deployment  
Runtime LLM  
RAG  
MCP  
Multi-agent architecture  
LLM fine-tuning  
Transformer training  
Attack graph  
SIEM integration  
Autonomous remediation  
Multi-cloud support

Các thành phần này không trực tiếp cần thiết để trả lời research questions và làm tăng đáng kể implementation workload.

Protocol cũng đã xác định nhiều thành phần trên nằm ngoài scope của nghiên cứu.

---

# **26\. Mapping giữa Architecture và Research Questions**

| Thành phần | Vai trò nghiên cứu |
| ----- | ----- |
| Terraform Corpus | Cung cấp experimental artifacts |
| Checkov | Phát hiện security misconfigurations |
| Normalizer | Chuẩn hóa findings |
| Context Manager | Đại diện deployment/business context |
| Feature Extractor | Biểu diễn technical context |
| Human Annotation | Tạo study-defined ground truth |
| Severity Baseline | Đối chứng không sử dụng context |
| Contextual Baseline | Kiểm tra giá trị của context mà không cần ML |
| Random Forest | Kiểm tra khả năng học contextual prioritization |
| Evaluation Engine | So sánh chất lượng ranking |
| Security Gate | Minh họa khả năng áp dụng vào DevSecOps |

Đối với **RQ1**, Terraform Corpus \+ Checkov \+ Normalizer hỗ trợ phân tích các loại security misconfiguration quan sát được trong corpus.

Đối với **RQ2**, Severity Baseline được so sánh với Contextual Baseline để đánh giá liệu contextual information có cải thiện prioritization hay không.

Đối với **RQ3**, Contextual Baseline được so sánh với Random Forest để đánh giá liệu ML có mang lại lợi ích bổ sung so với deterministic contextual scoring hay không.

Cấu trúc này phù hợp với mapping giữa research questions và experimental components trong protocol.

---

# **27\. Architecture khác gì Conceptual Framework và Workflow?**

Ba khái niệm này cần được phân biệt rõ trong luận văn.

### **Conceptual Framework**

Trả lời câu hỏi:

> **“Những khái niệm nào có quan hệ với nhau?”**

Ví dụ:

Security Finding  
\+  
Deployment Context  
\+  
Infrastructure Characteristics  
        ↓  
Contextual Security Priority

Conceptual Framework mô tả **logic nghiên cứu**.

---

### **System Architecture**

Trả lời câu hỏi:

> **“Hệ thống gồm những thành phần nào và dữ liệu đi qua chúng như thế nào?”**

Ví dụ:

Terraform  
→ Checkov  
→ Normalizer  
→ Context/Feature Builder  
→ Random Forest  
→ Ranking  
→ Security Gate

System Architecture mô tả **cấu trúc kỹ thuật của hệ thống**.

---

### **Research Workflow**

Trả lời câu hỏi:

> **“Nghiên cứu sẽ được thực hiện theo thứ tự nào?”**

Ví dụ:

Collect dataset  
→ Validate  
→ Scan  
→ Annotate  
→ Train  
→ Evaluate  
→ Analyze  
→ Write thesis

Workflow mô tả **quy trình thực hiện nghiên cứu**.

Do đó:

Conceptual Framework  
        ↓  
Giải thích WHY

System Architecture  
        ↓  
Giải thích WHAT / HOW SYSTEM WORKS

Research Workflow  
        ↓  
Giải thích HOW THE RESEARCH IS EXECUTED  
---

# **28\. Những điểm cần freeze trước khi implementation**

Kiến trúc tổng thể đã có thể cố định, nhưng một số chi tiết phương pháp luận trong tài liệu hiện tại vẫn cần được xác định rõ trước khi bắt đầu experiment chính.

### **1\. ML training target**

Cần xác định chính xác Random Forest sẽ học giá trị nào:

human\_rank

hay:

relevance\_grade

hay một priority target khác.

Tài liệu hiện tại xác định human ranking, relevance mapping và continuous model score, nhưng cần đảm bảo implementation sử dụng một định nghĩa target duy nhất và nhất quán.

### **2\. Severity mapping**

Do Checkov có thể không cung cấp severity trực tiếp, cần freeze severity mapping trước evaluation.

### **3\. Deterministic contextual formula**

Công thức và trọng số phải được freeze trước khi quan sát kết quả cuối của Random Forest để tránh điều chỉnh baseline nhằm tạo ra kết quả mong muốn.

### **4\. `check_id` có được dùng làm ML feature hay không**

`check_id` có thể chứa tín hiệu mạnh nhưng cũng có nguy cơ khiến model ghi nhớ loại rule thay vì học contextual prioritization.

Có thể xử lý bằng cách:

Main experiment: không dùng check\_id  
Optional ablation: có check\_id

hoặc thiết kế ngược lại, nhưng lựa chọn phải được ghi rõ trước experiment.

### **5\. Main validation strategy**

Cần thống nhất một protocol chính giữa:

Fixed family-based train/test split

và:

GroupKFold / Leave-One-Family-Out

Cả hai đều bảo vệ khỏi family leakage, nhưng thesis nên có một primary evaluation protocol rõ ràng.

---

# **29\. Kiến trúc cuối cùng đề xuất**

Kiến trúc có thể được tóm tắt thành năm tầng:

┌───────────────────────────────────────┐  
│ 1\. DATA / ARTIFACT LAYER              │  
│ Terraform \+ Scenario Metadata         │  
└──────────────────┬────────────────────┘  
                   ▼  
┌───────────────────────────────────────┐  
│ 2\. SECURITY ANALYSIS LAYER            │  
│ Validation → Checkov → Normalization  │  
└──────────────────┬────────────────────┘  
                   ▼  
┌───────────────────────────────────────┐  
│ 3\. CONTEXT & FEATURE LAYER            │  
│ Business Context                      │  
│ Infrastructure Features               │  
│ Feature Builder                       │  
└──────────────────┬────────────────────┘  
                   ▼  
┌───────────────────────────────────────┐  
│ 4\. PRIORITIZATION LAYER               │  
│ Severity Baseline                     │  
│ Contextual Baseline                   │  
│ Random Forest                         │  
└──────────────────┬────────────────────┘  
                   ▼  
┌───────────────────────────────────────┐  
│ 5\. EVALUATION / OPERATIONAL LAYER     │  
│ NDCG / Spearman / Statistics          │  
│ Ranking → Security Gate               │  
└───────────────────────────────────────┘

Kiến trúc này giữ đúng trọng tâm nghiên cứu:

> **Checkov phát hiện vấn đề bảo mật, Context mô tả hoàn cảnh của vấn đề, và Machine Learning học cách ưu tiên các vấn đề đó.**

Hay ngắn gọn hơn:

> **Scanner phát hiện — Context giải thích — ML ưu tiên.**

Điểm đóng góp của kiến trúc không nằm ở việc xây dựng một scanner mới hay một hệ thống DevSecOps hoàn chỉnh. Đóng góp nằm ở việc xây dựng một pipeline có thể kiểm chứng thực nghiệm xem **contextual information và Machine Learning có cải thiện security finding prioritization so với severity-based prioritization và deterministic contextual scoring hay không**.

# Workflow / Data Flow — Luồng xử lý

# **WORKFLOW / DATA FLOW — LUỒNG XỬ LÝ**

## **1\. Mục đích**

Workflow mô tả trình tự xử lý dữ liệu từ lúc thu thập Terraform artifact cho đến khi tạo ra kết quả ưu tiên security findings và đánh giá các phương pháp prioritization.

Nếu **System Architecture** trả lời câu hỏi:

> Hệ thống gồm những thành phần nào?

thì **Workflow / Data Flow** trả lời:

> Dữ liệu đi qua các thành phần đó theo thứ tự nào, được biến đổi thành gì ở từng bước, và kết quả của bước trước được sử dụng như thế nào ở bước tiếp theo?

Workflow tổng thể của nghiên cứu có thể tóm tắt như sau:

Published / GenAI-generated Terraform Artifacts  
                    │  
                    ▼  
           Dataset Acquisition  
                    │  
                    ▼  
        Provenance & Family Tracking  
                    │  
                    ▼  
          Terraform Validation  
                    │  
                    ▼  
             Checkov Scan  
                    │  
                    ▼  
            Raw Findings  
                    │  
                    ▼  
        Finding Normalization  
                    │  
                    ▼  
       Context Representation  
                    │  
                    ▼  
       Feature Extraction  
                    │  
                    ▼  
           Feature Dataset  
                    │  
           ┌────────┴────────┐  
           │                 │  
           ▼                 ▼  
   Human Annotation      Model Inputs  
           │                 │  
           ▼                 │  
    Ground Truth             │  
           │                 │  
           └────────┬────────┘  
                    ▼  
           Dataset Preparation  
                    │  
                    ▼  
          Family-based Split  
                    │  
          ┌─────────┼─────────┐  
          ▼         ▼         ▼  
       Severity   Context    Random  
       Baseline   Baseline   Forest  
          │         │         │  
          └─────────┼─────────┘  
                    ▼  
              Predicted Rankings  
                    │  
                    ▼  
              Evaluation Engine  
                    │  
             ┌──────┴──────┐  
             ▼             ▼  
       Ranking Metrics   Statistics  
       NDCG / Spearman   Wilcoxon / CI  
             │             │  
             └──────┬──────┘  
                    ▼  
             Research Results  
                    │  
                    ▼  
           Operational Prototype  
                    │  
                    ▼  
              Security Gate  
          PASS / REVIEW / BLOCK  
---

# **2\. Các luồng chính của hệ thống**

Toàn bộ workflow được chia thành bốn luồng chính:

FLOW A — DATA PREPARATION  
Terraform → Validate → Scan → Normalize

FLOW B — CONTEXT & GROUND TRUTH  
Normalized Findings → Context → Features → Human Ranking

FLOW C — MODELING & EVALUATION  
Research Dataset → Split → Baselines / RF → Ranking → Evaluation

FLOW D — OPERATIONAL INFERENCE  
New Terraform → Scan → Features → Trained Model → Ranking → Security Gate

Việc tách thành các flow giúp phân biệt rõ **quá trình xây dựng nghiên cứu** với **quá trình sử dụng model sau khi đã huấn luyện**.

---

# **3\. Flow A — Data Preparation**

## **3.1. Bước 1 — Thu thập Terraform Artifacts**

### **Input**

Published / reproducible  
AI-generated Terraform artifacts

Theo Research Protocol v2.3, nghiên cứu ưu tiên tái sử dụng các Terraform artifacts hoặc benchmark có nguồn gốc từ prior work thay vì tự xây dựng toàn bộ dataset từ đầu.

Dữ liệu ban đầu tạo thành:

TIER 1  
SOURCE CORPUS

Mỗi artifact cần giữ các metadata cần thiết cho provenance và experimental tracking.

Ví dụ:

source\_id  
source\_name  
artifact\_id  
family\_id  
terraform\_path  
provenance  
license

### **Output**

Source Corpus  
---

# **4\. Bước 2 — Dataset Filtering**

Các artifact trong Source Corpus không tự động được sử dụng cho experiment.

Chúng phải được lọc theo phạm vi nghiên cứu.

Các tiêu chí chính gồm:

AWS  
AND  
Terraform  
AND  
valid / processable  
AND  
Checkov scanable  
AND  
acceptable provenance/license  
AND  
at least one security finding

Các artifact đáp ứng tiêu chí tạo thành:

TIER 2  
RESEARCH CORPUS

Đối với prioritization benchmark, ưu tiên các scenario có nhiều findings hơn, đặc biệt là các scenario có ít nhất 3 hoặc 5 findings vì chúng hữu ích hơn cho NDCG@3 và NDCG@5.

### **Data Flow**

Source Corpus  
      │  
      ▼  
Eligibility Filtering  
      │  
 ┌────┴─────┐  
 │          │  
Eligible  Ineligible  
 │          │  
 ▼          ▼  
Research   Exclusion  
Corpus     Log

Các artifact bị loại vẫn nên được ghi nhận cùng lý do loại để bảo đảm reproducibility.

---

# **5\. Bước 3 — Gán Family ID**

Các Terraform artifacts có nguồn gốc hoặc cấu trúc liên quan cần được nhóm thành cùng một `family_id`.

Ví dụ:

Family F001  
 ├── Scenario S001-A  
 └── Scenario S001-B

Family F002  
 ├── Scenario S002-A  
 └── Scenario S002-B

`family_id` đóng vai trò đặc biệt quan trọng ở bước train/test split.

Mục tiêu là bảo đảm:

same family  
    ≠  
train AND test

Nếu hai variants gần giống nhau xuất hiện ở cả train và test, model có thể ghi nhớ đặc điểm của Terraform family thay vì generalize sang artifact chưa từng thấy.

---

# **6\. Bước 4 — Terraform Validation**

Mỗi Terraform artifact được kiểm tra trước khi security scanning.

### **Input**

Terraform Artifact

### **Processing**

terraform fmt  
      ↓  
terraform validate

### **Output**

validation\_status  
validation\_log

Luồng xử lý:

Terraform  
    │  
    ▼  
Validation  
    │  
 ┌──┴───┐  
 │      │  
PASS   FAIL  
 │      │  
 ▼      ▼  
Scan   Error Log

Artifact không thể xử lý phải được ghi lại trạng thái thay vì âm thầm loại khỏi dataset.

Validation và Checkov scanning là các bước riêng trong workflow, và phiên bản công cụ cần được cố định để tăng reproducibility.

---

# **7\. Bước 5 — Checkov Security Scan**

Terraform hợp lệ được đưa vào Checkov.

### **Input**

Validated Terraform

### **Processing**

Checkov Static Analysis

### **Output**

Raw Checkov JSON

Ví dụ dữ liệu thô:

check\_id  
check\_name  
resource  
resource\_type  
file\_path  
file\_line\_range  
check\_result  
severity

Workflow tại thời điểm này trả lời:

> Terraform artifact có những security misconfiguration nào được Checkov phát hiện?

Chưa trả lời:

> Finding nào cần xử lý trước?

Đó là nhiệm vụ của các bước prioritization sau.

---

# **8\. Bước 6 — Finding Normalization**

Raw Checkov output được chuyển sang một schema thống nhất.

### **Input**

Raw Checkov JSON

### **Processing**

Parse  
   ↓  
Clean  
   ↓  
Normalize  
   ↓  
Assign identifiers

### **Output**

Normalized Findings

Ví dụ:

finding\_id  
family\_id  
scenario\_id

check\_id  
check\_name

resource\_address  
resource\_type

file\_path  
start\_line  
end\_line

scanner\_severity

Workflow v2.3 xác định normalization là bước riêng trước annotation và modeling.

Một finding ở đây được hiểu là **scanner finding**. Nhiều Checkov findings có thể cùng liên quan đến một root cause, do đó không nên mặc định mỗi finding là một vulnerability hoàn toàn độc lập.

---

# **9\. Flow B — Context & Ground Truth**

Sau khi có normalized findings, workflow chuyển sang xây dựng contextual information và research ground truth.

Normalized Findings  
        │  
        ├───────────────┐  
        ▼               ▼  
Scenario Context   Infrastructure Facts  
        │               │  
        └───────┬───────┘  
                ▼  
         Feature Dataset  
                │  
                ▼  
        Human Annotation  
                │  
                ▼  
          Ground Truth  
---

# **10\. Bước 7 — Scenario Context Assignment**

Mỗi scenario được gắn contextual metadata.

Các biến context chính:

environment  
asset\_criticality  
data\_sensitivity

Ví dụ Scenario A:

{  
  "environment": "development",  
  "asset\_criticality": "low",  
  "data\_sensitivity": "low"  
}

Scenario B:

{  
  "environment": "production",  
  "asset\_criticality": "high",  
  "data\_sensitivity": "high"  
}

Trong contrastive A/B design:

Terraform A ≈ Terraform B

nhưng

Context A ≠ Context B

Thiết kế này cho phép kiểm tra phản ứng của prioritization method khi context thay đổi trong khi technical artifact được giữ giống hoặc tương đương.

Tuy nhiên:

Context thay đổi  
      ≠  
Ranking bắt buộc phải thay đổi

Human annotator vẫn phải xếp hạng dựa trên rationale của scenario thay vì bị ép tạo ra ranking khác giữa A và B.

---

# **11\. Bước 8 — Infrastructure Feature Extraction**

Song song với scenario context, hệ thống trích xuất các đặc điểm kỹ thuật có thể quan sát từ Terraform và security findings.

Ví dụ:

internet\_exposure  
privilege\_impact  
reachability

và khi có thể suy ra khách quan:

public\_access  
wildcard\_action  
wildcard\_resource  
encryption\_missing  
logging\_missing

Luồng:

Terraform  
   \+  
Normalized Finding  
        │  
        ▼  
Infrastructure Feature Extractor  
        │  
        ▼  
Technical Features

Feature phải được suy ra từ bằng chứng kỹ thuật, không dựa trên phỏng đoán.

Ví dụ:

CIDR \= 0.0.0.0/0  
        ↓  
internet\_exposure \= true

Trong khi:

resource name \= "critical\_db"

không đủ để tự động kết luận:

asset\_criticality \= high

Protocol phân biệt scenario/business context và finding/resource-level features.

---

# **12\. Bước 9 — Feature Construction**

Scenario context và infrastructure features được kết hợp với normalized finding.

Normalized Finding  
       \+  
Scenario Context  
       \+  
Infrastructure Features  
       │  
       ▼  
ML-ready Feature Record

Ví dụ:

finding\_id \= F001  
family\_id \= FM01  
scenario\_id \= SC01

environment \= production  
asset\_criticality \= high  
data\_sensitivity \= high

internet\_exposure \= 1  
privilege\_impact \= 1  
reachability \= 1

resource\_type \= aws\_s3\_bucket

Một nguyên tắc bắt buộc là:

Feature Extraction  
       ↓  
Feature Freeze  
       ↓  
Human Annotation

không phải:

Human Annotation  
       ↓  
Biết đáp án  
       ↓  
Tạo feature phù hợp với đáp án

Protocol yêu cầu finding-level features được xác định trước annotation để giảm nguy cơ leakage/circularity.

---

# **13\. Bước 10 — Human Ground Truth Annotation**

Sau khi features/context đã được xác định, các findings trong mỗi scenario được human annotator xếp hạng.

### **Input**

Scenario  
\+  
Security Findings  
\+  
Defined Context  
\+  
Annotation Rubric

### **Processing**

Ví dụ:

Finding F03 → Rank 1  
Finding F01 → Rank 2  
Finding F04 → Rank 3  
Finding F02 → Rank 4

### **Output**

human\_rank

Protocol hiện tại yêu cầu mỗi finding trong một scenario có unique rank.

Để sử dụng NDCG, rank được ánh xạ sang relevance:

Rank 1  → Relevance 3  
Rank 2  → Relevance 2  
Rank 3  → Relevance 1  
Rank 4+ → Relevance 0

Đây là relevance mapping được quy định trong protocol.

---

# **14\. Bước 11 — Tạo Prioritization Benchmark**

Sau annotation:

Features  
   \+  
Human Rank  
   \+  
Relevance  
       │  
       ▼  
Prioritization Benchmark

Đây là:

TIER 3  
PRIORITIZATION BENCHMARK

Một record cuối có thể có dạng:

family\_id  
scenario\_id  
finding\_id

scanner\_severity

environment  
asset\_criticality  
data\_sensitivity

internet\_exposure  
privilege\_impact  
reachability

resource\_type

human\_rank  
relevance\_grade

Research Corpus có thể lớn hơn Prioritization Benchmark vì không nhất thiết phải human-annotate toàn bộ findings đã thu thập. Đây là một chủ đích của Protocol v2.3 nhằm giảm annotation workload.

---

# **15\. Flow C — Modeling & Evaluation**

Đây là luồng thực nghiệm chính.

Prioritization Benchmark  
           │  
           ▼  
      Family Split  
           │  
    ┌──────┴──────┐  
    ▼             ▼  
Training         Test  
    │             │  
    ▼             │  
Model Training    │  
    │             │  
    └──────┬──────┘  
           ▼  
       Prediction  
           │  
           ▼  
        Ranking  
           │  
           ▼  
       Evaluation  
---

# **16\. Bước 12 — Family-Based Dataset Split**

Dataset được chia dựa trên `family_id`.

Không sử dụng:

random finding-level split

nếu điều đó làm các variants cùng family xuất hiện ở cả train và test.

Ví dụ đúng:

TRAIN  
 ├── Family A  
 ├── Family B  
 ├── Family C  
 └── Family D

TEST  
 ├── Family E  
 └── Family F

Ví dụ cần tránh:

Family A  
 ├── Scenario A1 → TRAIN  
 └── Scenario A2 → TEST

Protocol yêu cầu split theo family/scenario family để giảm data leakage.

---

# **17\. Bước 13 — Severity-Only Baseline**

Baseline đầu tiên chỉ sử dụng scanner severity.

Finding  
   ↓  
Scanner Severity  
   ↓  
Severity Score  
   ↓  
Sort  
   ↓  
Predicted Ranking

Mục đích của baseline này là tạo một điểm tham chiếu cho câu hỏi:

> Nếu chỉ sử dụng severity giống cách prioritization đơn giản thường làm, ranking đạt chất lượng như thế nào?

Trong pilot, Checkov có trường hợp trả về `severity=None`. Vì vậy severity mapping/policy cần được xác định và freeze trước evaluation.

---

# **18\. Bước 14 — Deterministic Contextual Baseline**

Baseline thứ hai bổ sung contextual information nhưng **không sử dụng ML**.

Severity  
   \+  
Environment  
   \+  
Criticality  
   \+  
Data Sensitivity  
   \+  
Exposure  
   \+  
Privilege Impact  
        │  
        ▼  
Deterministic Formula  
        │  
        ▼  
Contextual Priority Score  
        │  
        ▼  
Ranking

Mục đích là kiểm tra:

Severity-only  
      vs  
Context-aware rule

Nếu contextual baseline tốt hơn severity-only, kết quả cung cấp bằng chứng cho giá trị của context trong benchmark đang đánh giá.

Baseline này cũng tạo đối chứng quan trọng cho ML:

Contextual Rule  
      vs  
Random Forest

để tránh việc mặc định rằng sử dụng Machine Learning đương nhiên sẽ tốt hơn một scoring rule đơn giản.

---

# **19\. Bước 15 — Random Forest Training**

Random Forest là ML model chính.

### **Training Flow**

Training Families  
       │  
       ▼  
Feature Matrix X  
       \+  
Training Target y  
       │  
       ▼  
Preprocessing  
       │  
       ▼  
RandomForestRegressor  
       │  
       ▼  
Model Training  
       │  
       ▼  
Trained Model

Random Forest được lựa chọn làm primary ML model trong workflow; XGBoost chỉ là optional extension.

---

# **20\. Bước 16 — Priority Prediction**

Model được áp dụng lên unseen test families.

Test Finding  
     │  
     ▼  
Feature Vector  
     │  
     ▼  
Trained Random Forest  
     │  
     ▼  
Priority Score

Ví dụ:

F001 → 0.91  
F004 → 0.82  
F003 → 0.47  
F002 → 0.21

Sau đó findings trong cùng scenario được sort:

Priority Score  
      ↓  
Descending Sort  
      ↓  
Predicted Ranking

Kết quả:

Rank 1 → F001  
Rank 2 → F004  
Rank 3 → F003  
Rank 4 → F002

Điểm số chủ yếu phục vụ việc tạo thứ tự ưu tiên; mục tiêu nghiên cứu cuối cùng là **ranking quality**.

---

# **21\. Bước 17 — Ranking Evaluation**

Mỗi method tạo ra ranking riêng:

Human Ground Truth  
        │  
        ├──────── Severity Ranking  
        │  
        ├──────── Contextual Ranking  
        │  
        └──────── Random Forest Ranking

Các ranking này được so sánh với human ground truth.

Primary metrics:

NDCG@3  
NDCG@5

Secondary metric:

Spearman Rank Correlation

MAE/RMSE có thể được sử dụng như diagnostic metrics nếu phù hợp với target được freeze, nhưng ranking metrics là trọng tâm của evaluation.

---

# **22\. Bước 18 — Scenario-Level Evaluation**

Metric được tính theo scenario thay vì chỉ tạo một con số tổng hợp duy nhất.

Ví dụ:

Scenario   Severity   Context   RF  
\----------------------------------  
S001       0.61       0.79      0.84  
S002       0.55       0.72      0.70  
S003       0.67       0.75      0.81  
...

Sau đó mới tổng hợp:

Mean / Median  
Confidence Interval  
Effect Size

Điều này cho phép quan sát không chỉ model nào có average metric khác nhau, mà còn:

Trong bao nhiêu scenario phương pháp cải thiện?  
Mức cải thiện lớn hay nhỏ?  
Kết quả có ổn định giữa các scenario không?  
---

# **23\. Bước 19 — Statistical Analysis**

Nếu kích thước dữ liệu cho phép, workflow sử dụng paired scenario-level analysis.

Ví dụ:

NDCG\_RF(S001) \- NDCG\_Context(S001)  
NDCG\_RF(S002) \- NDCG\_Context(S002)  
NDCG\_RF(S003) \- NDCG\_Context(S003)  
...

Sau đó phân tích bằng:

Wilcoxon signed-rank test  
Effect size  
Bootstrap 95% confidence interval

Protocol đã xác định paired statistical analysis, effect size và bootstrap confidence interval là các thành phần của evaluation.

Kết quả không nên chỉ được diễn giải dựa trên:

p \< 0.05

mà còn phải xem xét:

direction of effect  
magnitude of effect  
confidence interval  
scenario consistency  
---

# **24\. Bước 20 — Contrastive Context Analysis**

Một experiment phụ có thể sử dụng các cặp A/B.

Same / Equivalent Terraform  
            │  
      ┌─────┴─────┐  
      ▼           ▼  
 Context A     Context B  
      │           │  
      ▼           ▼  
 Score A       Score B  
      │           │  
      └─────┬─────┘  
            ▼  
     Δ Priority Score

Với matched finding:

Δscore \= score\_B \- score\_A

Finding được match dựa trên các thông tin như:

check\_id  
\+  
normalized resource address

Sau đó kết quả được aggregate ở mức family để tránh xem các findings liên quan trong cùng family như những quan sát hoàn toàn độc lập. Đây là thiết kế B2 được mô tả trong protocol.

Experiment này trả lời câu hỏi phụ:

> Khi technical finding được giữ giống hoặc tương đương nhưng deployment/business context thay đổi, prioritization method phản ứng như thế nào?

---

# **25\. Bước 21 — Exploratory Analysis**

Sau primary experiments, có thể thực hiện exploratory analysis.

Ví dụ:

Feature importance  
Feature ablation  
Error analysis  
Category-level analysis  
Resource-type analysis

Mục tiêu là hỗ trợ câu hỏi:

> Những contextual factors nào có liên quan nhiều nhất đến kết quả prioritization của model?

Đây là exploratory analysis, không nên được trình bày như causal evidence.

---

# **26\. Flow D — Operational Inference**

Research workflow và operational workflow phải được tách riêng.

Sau khi Random Forest đã được huấn luyện, một Terraform artifact mới có thể đi qua:

New Terraform  
      │  
      ▼  
Terraform Validation  
      │  
      ▼  
Checkov Scan  
      │  
      ▼  
Finding Normalization  
      │  
      ▼  
Context Input  
      │  
      ▼  
Infrastructure Feature Extraction  
      │  
      ▼  
Feature Builder  
      │  
      ▼  
Trained Random Forest  
      │  
      ▼  
Priority Scores  
      │  
      ▼  
Finding Ranking  
      │  
      ▼  
Security Gate

Điểm khác biệt quan trọng:

RESEARCH WORKFLOW  
contains  
Human Annotation \+ Ground Truth

OPERATIONAL WORKFLOW  
does NOT contain  
Human Rank / Ground Truth  
---

# **27\. Security Gate Flow**

Sau khi có ranking:

Ranked Findings  
       │  
       ▼  
Operational Policy  
       │  
 ┌─────┼──────┐  
 ▼     ▼      ▼  
PASS REVIEW BLOCK

Ví dụ:

Terraform  
    ↓  
Checkov finds 8 issues  
    ↓  
ML prioritizes 8 issues  
    ↓  
Top priority finding \= F003  
    ↓  
Gate Policy  
    ↓  
REVIEW

Security Gate là prototype minh họa khả năng tích hợp kết quả prioritization vào DevSecOps workflow, không phải scientific ground truth và không phải production enforcement platform. Protocol và workflow hiện tại giới hạn prototype ở mức lightweight gate với CLI/JSON là đủ.

---

# **28\. Data Transformation Flow**

Một cách khác để nhìn workflow là quan sát **dữ liệu thay đổi hình dạng như thế nào**.

STAGE 1  
Terraform Files  
(.tf)  
        ↓  
STAGE 2  
Raw Checkov Results  
(JSON)  
        ↓  
STAGE 3  
Normalized Findings  
(CSV / JSON)  
        ↓  
STAGE 4  
Context \+ Technical Features  
(CSV / structured dataset)  
        ↓  
STAGE 5  
Annotated Research Dataset  
(features \+ human\_rank)  
        ↓  
STAGE 6  
Train/Test Dataset  
        ↓  
STAGE 7  
Model Predictions  
(priority\_score)  
        ↓  
STAGE 8  
Scenario Rankings  
        ↓  
STAGE 9  
Evaluation Results  
(NDCG / Spearman / statistics)  
        ↓  
STAGE 10  
Operational Output  
(JSON / CLI)

Như vậy, hệ thống không đưa Terraform trực tiếp vào Random Forest.

Luồng thực tế là:

Terraform  
   ↓  
Security Analysis  
   ↓  
Structured Findings  
   ↓  
Contextual Representation  
   ↓  
Tabular Features  
   ↓  
Machine Learning  
---

# **29\. Ví dụ Data Flow cho một Finding**

Giả sử Checkov phát hiện một security finding.

### **Stage 1 — Terraform**

aws\_security\_group.example  
allows ingress from 0.0.0.0/0

### **Stage 2 — Scanner**

Checkov  
   ↓  
Finding F001

### **Stage 3 — Normalization**

finding\_id      \= F001  
resource\_type   \= aws\_security\_group  
family\_id       \= FM01  
scenario\_id     \= SC01

### **Stage 4 — Infrastructure Feature**

internet\_exposure \= 1

### **Stage 5 — Scenario Context**

environment       \= production  
asset\_criticality \= high  
data\_sensitivity  \= high

### **Stage 6 — Feature Record**

F001  
production  
high  
high  
internet\_exposure \= 1  
...

### **Stage 7 — Human Annotation**

human\_rank \= 1  
relevance \= 3

### **Stage 8 — ML Prediction**

Random Forest  
      ↓  
priority\_score \= 0.91

### **Stage 9 — Ranking**

Scenario SC01

1\. F001   0.91  
2\. F004   0.78  
3\. F002   0.52  
4\. F003   0.31

### **Stage 10 — Evaluation**

Predicted Ranking  
       vs  
Human Ranking  
       ↓  
NDCG@3 / NDCG@5 / Spearman

Đây là một ví dụ minh họa cho cấu trúc dữ liệu của workflow; các giá trị score chỉ nhằm giải thích luồng, không phải kết quả thực nghiệm của nghiên cứu.

---

# **30\. Mapping Workflow với Research Questions**

## **RQ1 — Security Misconfiguration Analysis**

Terraform Corpus  
      ↓  
Checkov  
      ↓  
Normalized Findings  
      ↓  
Descriptive Analysis

Kết quả có thể mô tả:

finding categories  
check frequency  
resource types  
scenario/family distribution

RQ1 chỉ mô tả những gì quan sát được trong evaluated corpus, không đại diện cho toàn bộ Terraform do Generative AI tạo ra.

---

## **RQ2 — Contextual Prioritization**

Ground Truth  
      │  
      ├── Severity-only  
      │  
      └── Contextual Baseline  
               │  
               ▼  
             NDCG

Mục tiêu:

> Đánh giá contextual information có cải thiện prioritization so với severity-only trong benchmark hay không.

---

## **RQ3 — Machine Learning**

Ground Truth  
      │  
      ├── Contextual Baseline  
      │  
      └── Random Forest  
               │  
               ▼  
       Ranking Evaluation

Mục tiêu:

> Đánh giá Random Forest có cung cấp lợi ích bổ sung so với deterministic contextual scoring hay không.

Mapping giữa các research questions và experimental components được xác định trong protocol.

---

# **31\. Workflow và Data Leakage Control**

Một số checkpoint cần được đặt trực tiếp trong workflow.

CHECKPOINT 1  
Feature definitions frozen  
BEFORE  
Human annotation

CHECKPOINT 2  
Annotation rubric frozen  
BEFORE  
Model evaluation

CHECKPOINT 3  
Severity mapping frozen  
BEFORE  
Final comparison

CHECKPOINT 4  
Context baseline formula frozen  
BEFORE  
Final model comparison

CHECKPOINT 5  
family\_id respected  
DURING  
Train/test split

CHECKPOINT 6  
Test data not used  
DURING  
Model tuning

Điều này đặc biệt quan trọng vì nguy cơ lớn của nghiên cứu không chỉ là traditional data leakage mà còn là **construct circularity**.

Ví dụ cần tránh:

Annotator:  
internet exposure → priority HIGH

           ↓

Model Feature:  
internet\_exposure \= 1

           ↓

Model learns:  
internet exposure → HIGH

           ↓

Conclusion:  
"ML discovered that exposure determines priority"

Trong trường hợp này, model có thể chủ yếu học lại annotation rubric.

Do đó kết quả cần được diễn giải cẩn thận là khả năng **học và generalize study-defined contextual prioritization**, không phải tự động chứng minh model đã khám phá “true security risk”.

---

# **32\. Failure Handling Flow**

Workflow phải xử lý failure ở từng stage.

### **Terraform Failure**

Terraform  
    ↓  
Validation FAIL  
    ↓  
Record failure  
    ↓  
Do not continue to normal scan pipeline

### **Scanner Failure**

Checkov  
    ↓  
Execution FAIL  
    ↓  
Record scanner version  
command  
error message

### **Missing Feature**

Cannot objectively determine feature  
              ↓  
         UNKNOWN / NA

Không tự suy đoán.

### **NDCG Eligibility**

Scenario findings \< 5  
        ↓  
Not eligible for NDCG@5

nhưng scenario có thể vẫn đủ điều kiện cho metric hoặc phân tích khác.

Protocol quy định failure handling và yêu cầu không thay đổi dataset hoặc annotation chỉ để làm cho hypothesis thành công.

---

# **33\. Reproducibility Flow**

Mỗi experiment cần lưu:

Experiment ID  
      │  
      ├── Dataset version  
      ├── Feature schema version  
      ├── Annotation version  
      ├── Train/test families  
      ├── Random seed  
      ├── Model parameters  
      ├── Checkov version  
      ├── Python/dependency versions  
      └── Evaluation results

Điều này cho phép tái tạo:

Input  
  ↓  
Processing  
  ↓  
Training  
  ↓  
Prediction  
  ↓  
Evaluation

thay vì chỉ lưu final metric.

---

# **34\. Workflow triển khai tối thiểu**

Đối với phạm vi luận văn, workflow bắt buộc nên dừng ở:

1\. Collect Terraform artifacts  
          ↓  
2\. Track provenance/family  
          ↓  
3\. Validate Terraform  
          ↓  
4\. Run Checkov  
          ↓  
5\. Normalize findings  
          ↓  
6\. Assign scenario context  
          ↓  
7\. Extract technical features  
          ↓  
8\. Freeze feature definitions  
          ↓  
9\. Human annotation  
          ↓  
10\. Build prioritization benchmark  
          ↓  
11\. Family-based split  
          ↓  
12\. Severity baseline  
          ↓  
13\. Contextual baseline  
          ↓  
14\. Random Forest  
          ↓  
15\. Generate rankings  
          ↓  
16\. NDCG / Spearman evaluation  
          ↓  
17\. Statistical / error analysis  
          ↓  
18\. Security Gate CLI/JSON  
          ↓  
19\. Report results

Đây là **core research workflow**.

---

# **35\. Optional Workflow**

Chỉ sau khi core workflow hoạt động ổn định mới bổ sung:

Core Workflow  
      │  
      ├── Contrastive A/B Analysis  
      │  
      ├── Feature Importance  
      │  
      ├── Feature Ablation  
      │  
      ├── XGBoost  
      │  
      ├── Second-annotator subset  
      │  
      └── GitHub Actions Integration

Các phần này không nên chặn tiến độ hoàn thành primary experiments.

XGBoost được xác định là optional trong workflow hiện tại.

---

# **36\. Những workflow không thuộc phạm vi**

Không mở rộng workflow sang:

Terraform  
   ↓  
Deploy real AWS  
   ↓  
Runtime attack simulation

hoặc:

Terraform  
   ↓  
LLM  
   ↓  
RAG  
   ↓  
Multi-agent  
   ↓  
Autonomous remediation

hoặc:

Multi-cloud  
   ↓  
AWS \+ Azure \+ GCP

Các hướng này nằm ngoài scope đã freeze và không cần thiết để trả lời các research questions chính.

---

# **37\. Workflow tổng thể đề xuất**

Luồng hoàn chỉnh có thể biểu diễn bằng bốn phase.

══════════════════════════════════════════════  
PHASE 1 — DATA PREPARATION  
══════════════════════════════════════════════

Prior-work / GenAI Terraform  
              ↓  
       Source Corpus  
              ↓  
      Eligibility Filter  
              ↓  
      Research Corpus  
              ↓  
    Terraform Validation  
              ↓  
        Checkov Scan  
              ↓  
      Normalize Findings

══════════════════════════════════════════════  
PHASE 2 — BENCHMARK CONSTRUCTION  
══════════════════════════════════════════════

      Normalized Findings  
              ↓  
      ┌───────┴────────┐  
      ↓                ↓  
Scenario Context   Technical Features  
      │                │  
      └───────┬────────┘  
              ↓  
       Feature Records  
              ↓  
       Human Annotation  
              ↓  
   Prioritization Benchmark

══════════════════════════════════════════════  
PHASE 3 — EXPERIMENT  
══════════════════════════════════════════════

   Prioritization Benchmark  
              ↓  
       Family-based Split  
              ↓  
     ┌────────┼────────┐  
     ↓        ↓        ↓  
 Severity   Context   Random  
 Baseline   Baseline  Forest  
     │        │        │  
     └────────┼────────┘  
              ↓  
       Priority Scores  
              ↓  
       Finding Rankings  
              ↓  
      NDCG / Spearman  
              ↓  
   Statistical Analysis  
              ↓  
       Research Results

══════════════════════════════════════════════  
PHASE 4 — PROTOTYPE  
══════════════════════════════════════════════

        New Terraform  
              ↓  
           Checkov  
              ↓  
          Normalize  
              ↓  
     Context \+ Features  
              ↓  
       Trained Model  
              ↓  
       Priority Score  
              ↓  
          Ranking  
              ↓  
       Security Gate  
              ↓  
     PASS / REVIEW / BLOCK  
---

# **38\. Quan hệ giữa Architecture và Workflow**

System Architecture và Workflow sử dụng cùng các thành phần nhưng nhìn từ hai góc độ khác nhau.

SYSTEM ARCHITECTURE  
        │  
        │ describes  
        ▼  
"What components exist?"

Checkov  
Normalizer  
Context Manager  
Feature Builder  
Random Forest  
Evaluation Engine  
Security Gate

Trong khi:

WORKFLOW / DATA FLOW  
        │  
        │ describes  
        ▼  
"What happens first, next, and last?"

Collect  
  ↓  
Validate  
  ↓  
Scan  
  ↓  
Normalize  
  ↓  
Contextualize  
  ↓  
Annotate  
  ↓  
Train  
  ↓  
Predict  
  ↓  
Evaluate  
  ↓  
Gate

Do đó, Architecture không nên thay thế Workflow và Workflow cũng không nên thay thế Architecture.

---

# **39\. Tóm tắt Workflow**

Toàn bộ luồng nghiên cứu có thể rút gọn thành:

Terraform  
   ↓  
Checkov  
   ↓  
Security Findings  
   ↓  
Normalization  
   ↓  
Context \+ Infrastructure Features  
   ↓  
Human Ground Truth  
   ↓  
Prioritization Benchmark  
   ↓  
Severity Baseline  
vs  
Contextual Baseline  
vs  
Random Forest  
   ↓  
Priority Ranking  
   ↓  
NDCG / Spearman / Statistical Analysis  
   ↓  
Research Findings  
   ↓  
Security Gate Prototype

Logic trung tâm của workflow là:

> **Terraform cung cấp artifact → Checkov phát hiện vấn đề → Context bổ sung ý nghĩa → Human annotation xác định reference ranking → Baselines và Machine Learning tạo predicted ranking → Evaluation đo chất lượng ranking → Security Gate minh họa khả năng ứng dụng vào DevSecOps.**

Workflow này bảo đảm đề tài không chỉ dừng ở việc xây dựng một công cụ, mà tạo thành một **experimental research pipeline** có dataset, ground truth, baseline, ML model, evaluation và reproducibility rõ ràng.

# Dataset & Ground Truth Design — Thiết kế dữ liệu

# **Dataset & Ground Truth Design cho đề tài Context-Aware ML for Security Risk Prioritization of GenAI-Generated Terraform**

## **Tóm tắt điều hành**

Đối với đề tài của bạn, **Dataset & Ground Truth là phần quan trọng nhất và cũng là phần rủi ro nhất của toàn bộ luận văn**. Random Forest về mặt implementation tương đối đơn giản; ngược lại, nếu dataset bị leakage, provenance không rõ, feature được tạo sau khi nhìn label, hoặc human ranking không có quy trình rõ ràng thì kết quả ML dù đẹp cũng khó bảo vệ về mặt khoa học. Chính Protocol v2.3 của bạn đã chuyển trọng tâm sang chiến lược hợp lý hơn: **REUSE → REPRODUCE → EXTEND → EVALUATE**, chia dữ liệu thành Source Corpus → Research Corpus → Prioritization Benchmark thay vì tự sinh toàn bộ benchmark. fileciteturn0file0

**Kết luận chính của báo cáo này:** thiết kế v2.3 là đúng hướng, nhưng với một sinh viên, lần đầu làm ML và chỉ có khoảng 8–10 tuần làm việc thực chất trước buffer, **không nên ép đạt 40–60 families / 80–120 scenarios bằng mọi giá**. Protocol vốn cũng xác định đây chỉ là planning target. fileciteturn0file0 Mức thực tế tôi khuyến nghị là khoảng **24–36 independent families, 48–72 contextual scenarios và khoảng 250–400 annotated findings**, với ưu tiên cao hơn cho số scenario đủ ≥5 findings, diversity và chất lượng annotation. Mức tối thiểu có thể bảo vệ được nếu thời gian xấu là khoảng **18–24 families, 36–48 contextual scenarios, 150–250 findings**, đồng thời cố gắng có khoảng **15–20 scenario đủ điều kiện cho NDCG@5**, phù hợp target thống kê ban đầu trong Blueprint. fileciteturn0file2 Đây là **planning recommendation**, không phải kết quả power analysis hay một ngưỡng thống kê phổ quát.

Nguồn dữ liệu tốt nhất hiện tại là **GenIaC-SecBench** vì đây là benchmark công khai mới, trực tiếp về security của LLM-generated IaC, có 100 scenarios, 1.196 generated artifacts, 38.803 scanner findings và raw scan results; dataset card cũng cho biết Terraform là subset đáng tin cậy nhất với 836/1.196 artifacts. Dữ liệu do dự án tạo được phát hành CC-BY-4.0, trong khi human reference corpus giữ license của các upstream project. [*\[1\]*](https://huggingface.co/datasets/AnimeshShaw/GenIaC-SecBench) Một nguồn trực tiếp khác là nghiên cứu **Security-First Evaluation of Text-to-Terraform**, đánh giá bảy model trên 17 AWS Terraform scenarios và công bố artifacts; tuy nhiên phải xác minh license cụ thể của repository artifact trước khi redistribute. [*\[2\]*](https://arxiv.org/abs/2608.02672) **IaC-Eval** là nguồn supplemental tốt vì có 458 human-curated AWS/Terraform questions và repository MIT, nhưng nó là benchmark code generation chứ không phải contextual-security-prioritization benchmark. [*\[3\]*](https://github.com/autoiac-project/iac-eval) **IaCSecBench** có thể dùng làm controlled/security reference hoặc QA corpus; nó có 56 admissible cases và repository MIT, nhưng không nên trộn nó vào tập “GenAI-generated” nếu provenance không cho thấy artifact do GenAI sinh. [*\[4\]*](https://github.com/mchittineni/iacsecbench)

Bốn quyết định cần **freeze trước khi annotation chính thức** là:

| Quyết định | Khuyến nghị |
| :---- | :---- |
| Đơn vị độc lập | family\_id, không phải finding |
| Ground truth gốc | human\_rank \= 1..N trong từng scenario |
| NDCG relevance | Rank 1→3, Rank 2→2, Rank 3→1, Rank 4+→0 |
| Technical features | Freeze trước annotation; chỉ dùng evidence khách quan |
| Severity | Giữ scanner\_severity\_raw nguyên trạng; severity baseline dùng mapping riêng đã freeze |
| Split | family\_id không được xuất hiện ở nhiều split |
| Annotation | Blind với model output, NDCG, baseline prediction; khuyến nghị ẩn cả severity baseline |
| ML target | Freeze một transform từ human rank trước training; không tự tạo synthetic labels |

Mapping NDCG hiện tại của Protocol v2.3 là phù hợp với bài toán top-priority ranking và phải giữ nguyên sau khi benchmark được freeze. NDCG đánh giá liệu các item có relevance cao có được model đưa lên đầu ranking hay không; k cho phép đánh giá riêng top-3/top-5. fileciteturn0file0 [*\[5\]*](https://scikit-learn.org/dev/modules/generated/sklearn.metrics.ndcg_score.html)

Một điểm cần bổ sung vào protocol trước ML: **human rank là ground truth chuẩn, nhưng RandomForestRegressor cần một numeric target**. Tôi khuyến nghị không dùng trực tiếp NDCG relevance 3,2,1,0 làm training target vì mọi finding từ rank 4 trở xuống sẽ bị collapse về cùng 0\. Thay vào đó có thể derive:

với scenario có . Khi đó rank 1 \= 1, rank cuối \= 0 và toàn bộ thứ tự vẫn được giữ. Đây **không phải synthetic label**, mà là deterministic transformation của human rank. Tuy nhiên, vì đây chưa được freeze trong v2.3, nó phải được ghi thành một quyết định methodology trước khi training, không được chọn sau khi xem kết quả model.

Luồng dữ liệu cuối cùng nên như sau:

flowchart TD  
 	A\[Public / Prior-work / GenAI Terraform\] \--\> B\[Source Corpus\]  
 	B \--\> C{Provenance \+ License \+ AWS \+ Terraform}  
 	C \--\>|Không đạt| X\[Exclusion Log\]  
 	C \--\>|Đạt| D\[terraform init \-backend=false\]  
 	D \--\> E\[terraform validate\]  
 	E \--\>|Fail| X  
 	E \--\>|Pass| F\[Checkov 3.3.17 \- JSON\]  
 	F \--\> G\[Raw Findings \- Immutable\]  
 	G \--\> H\[Finding Normalization\]  
 	H \--\> I\[Objective Feature Extraction\]  
 	I \--\> J\[Research Corpus\]  
 	J \--\> K\[Predefined Stratified Family Selection\]  
 	K \--\> L\[Context A/B Metadata\]  
 	L \--\> M\[Prioritization Benchmark\]  
 	M \--\> N\[Blind Human Annotation\]  
 	N \--\> O\[Frozen Human Rank\]  
 	O \--\> P\[Derived Relevance / ML Target\]  
 	P \--\> Q\[Family-based Split\]  
 	Q \--\> R\[Severity Baseline / Context Baseline / RF\]  
 	R \--\> S\[NDCG@3 / NDCG@5 / Spearman\]

Mấu chốt là: **Model chỉ xuất hiện sau khi dataset, features, annotation và split rules đã freeze**. Đó là hàng rào quan trọng nhất chống “làm dataset theo kết quả ML”.

## **Kiến trúc dataset và chiến lược nguồn**

Thiết kế ba tầng trong Protocol v2.3 nên được giữ nguyên. Nó giải quyết rất đúng bài toán nguồn lực của bạn: corpus lớn dùng để phân tích RQ1 không nhất thiết phải được annotate, trong khi benchmark nhỏ hơn mới cần human ground truth. fileciteturn0file0

TIER 1 — SOURCE CORPUS  
 Toàn bộ candidate artifacts có provenance/license kiểm tra được  
              	↓  
 TIER 2 — RESEARCH CORPUS  
 AWS \+ Terraform \+ validate PASS \+ Checkov scanable  
 \+ provenance acceptable \+ có in-scope finding  
              	↓  
 TIER 3 — PRIORITIZATION BENCHMARK  
 Subset theo selection rules đã freeze  
 \+ đủ finding density/diversity  
 \+ contextual scenarios  
 \+ human annotation

**Source Corpus** nên rộng; **Research Corpus** nên sạch; **Prioritization Benchmark** nên nhỏ hơn nhưng “đậm đặc” về thông tin. Không nên cố làm cả ba có cùng kích thước.

Các nguồn ưu tiên nên được đánh giá như sau:

| Nguồn | Độ phù hợp | Vai trò nên dùng | Lưu ý |
| :---- | :---- | :---- | :---- |
| **GenIaC-SecBench** | Rất cao | Primary source corpus | Có generated IaC, raw scanner data, model/scenario metadata; phải filter AWS \+ Terraform |
| **Security-First Text-to-Terraform** | Rất cao | Direct GenAI Terraform supplement | AWS Terraform trực tiếp; phải xác minh license artifact trước redistribute |
| **IaC-Eval** | Cao cho source material | Supplemental tasks/artifacts | AWS/Terraform nhưng không phải ground truth security prioritization |
| **IaCSecBench** | Trung bình–cao | Controlled security reference / QA | Có labelled security cases nhưng không mặc định là GenAI-generated |
| **Pilot hiện tại của bạn** | Cao cho methodology QA | Calibration / pipeline test | Không mặc định dùng làm final v2.3 benchmark |
| **Controlled additions tự xây** | Chỉ khi cần | Fill missing category/resource coverage | Không dùng để “cứu metric” |

GenIaC-SecBench đặc biệt hữu ích vì dataset card không chỉ cung cấp generated artifacts mà còn raw findings và metadata theo scenario/model; nó cũng công khai một limitation rất liên quan đến đề tài của bạn: các Checkov findings trong corpus đó có severity UNKNOWN, trong khi các severity tier trong phân tích của họ đến từ các scanner khác. Điều này củng cố quyết định của bạn rằng **severity baseline phải có policy riêng và không được giả vờ rằng một mapping tự xây là “Checkov severity”**. [*\[6\]*](https://huggingface.co/datasets/AnimeshShaw/GenIaC-SecBench)

IaC-Eval phù hợp hơn để tạo diversity về Terraform tasks/resources: repository chính thức mô tả benchmark Terraform cho AWS với 458 human-curated questions và giấy phép MIT. Nhưng labels hoặc evaluation oracle của IaC-Eval không trả lời câu hỏi “finding nào nên remediate trước trong context X”, vì vậy không được tái sử dụng chúng làm priority ground truth. [*\[3\]*](https://github.com/autoiac-project/iac-eval)

IaCSecBench là nguồn hữu ích để kiểm tra pipeline hoặc lấy controlled security examples; repository hiện công bố 56 admissible cases, trong đó 30 vulnerable và 26 compliant, và license MIT. Nhưng đây là benchmark security gate, do đó nếu artifact không có provenance GenAI thì phải đánh dấu riêng trong dataset, không được làm tăng artificial count của “GenAI-generated Terraform”. [*\[4\]*](https://github.com/mchittineni/iacsecbench)

**Eligibility filter** nên thực hiện ở artifact/family level trước khi nhìn kết quả prioritization:

MUST  
 AWS  
 AND Terraform  
 AND provenance known  
 AND license/usage acceptable  
 AND artifact retrievable/reproducible  
 AND terraform validate \= PASS  
 AND Checkov execution \= PASS  
 AND ≥ 1 in-scope finding

 PREFERRED FOR PRIORITIZATION BENCHMARK  
 ≥ 3 in-scope findings  
 prefer ≥ 5  
 security-category diversity  
 resource diversity  
 context relevance  
 no near-duplicate domination

Đây gần như đúng với v2.3 và Workflow hiện tại. fileciteturn0file0 fileciteturn0file1

Điểm cần phân biệt là: **Research Corpus được phép có scenario chỉ có một finding**, vì RQ1 vẫn dùng được cho descriptive security analysis. Nhưng Prioritization Benchmark nên ưu tiên scenario ≥3 findings và đặc biệt ≥5 findings để ranking có ý nghĩa hơn. Protocol của bạn cũng chủ động ưu tiên NDCG@5 eligibility hơn raw artifact count. fileciteturn0file0

Sampling nên là **predefined stratified family sampling**, không phải random finding sampling. Các strata nên xem xét đồng thời:

| Trục sampling | Mục tiêu |
| :---- | :---- |
| Source | Không để một public benchmark chiếm toàn bộ |
| Base family/task | Tăng effective independence |
| Security category | Tránh dataset chỉ toàn logging/encryption |
| Resource type | S3/IAM/RDS/SG/... không quá lệch |
| Finding count | Có đủ scenario cho NDCG@3 và NDCG@5 |
| Terraform complexity | Có simple \+ moderate/complex |
| Generation source/model | Diversity nếu metadata có sẵn |
| Context suitability | Finding phải có khả năng phân tích context hợp lý |

Nếu một stratum có quá nhiều candidates, bạn có thể random-select **family** bên trong stratum bằng seed cố định. Không được chọn individual finding vì như vậy vừa làm mất tính nguyên vẹn của scenario vừa tạo nguy cơ selection bias.

Không truncate một scenario từ 12 findings xuống 5 chỉ để annotation nhẹ hơn. Workflow v2.3 đã ghi rõ không truncate findings chỉ để đạt 4–6 findings. fileciteturn0file1 Nếu một scenario quá lớn đến mức annotation không khả thi, hoặc annotate toàn bộ in-scope findings, hoặc loại cả family theo một rule đã định nghĩa trước.

Với Terraform validation, nên sử dụng:

terraform init \-backend=false  
 terraform validate \-json

HashiCorp xác định terraform validate kiểm tra syntax và internal consistency nhưng **không xác minh remote services, state hay provider APIs**; command cần working directory đã initialize và \-backend=false cho phép initialization phục vụ validation mà không truy cập configured backend. Vì vậy validate \= PASS chỉ là admission criterion về technical validity, không phải bằng chứng configuration deploy được hay an toàn. [*\[7\]*](https://developer.hashicorp.com/terraform/cli/commands/validate)

Provider version cũng phải được pin. HashiCorp ghi rõ .terraform.lock.hcl lưu chính xác provider versions đã chọn để các lần chạy sau giữ consistency. Vì vậy cần lưu lock file hoặc ít nhất manifest về provider version cho từng artifact/family. [*\[8\]*](https://developer.hashicorp.com/terraform/tutorials/aws-get-started/aws-create)

Về Checkov, Workflow đã freeze **3.3.17** và phiên bản này thực sự được phát hành ngày 10 tháng 9 năm 2026 trên PyPI, kèm provenance attestation và checksum. Không nên tự động nâng version giữa quá trình xây corpus và final rerun, vì thay đổi rule set có thể làm population findings thay đổi. fileciteturn0file1 [*\[9\]*](https://pypi.org/project/checkov/3.3.17/)

Command nên cố định ở dạng tương đương:

checkov \\  
   \--framework terraform \\  
   \--directory \<artifact\> \\  
   \--output json

Checkov CLI chính thức hỗ trợ Terraform framework và JSON output. [*\[10\]*](https://www.checkov.io/2.Basics/CLI%20Command%20Reference.html) Raw JSON phải được giữ immutable để sau này bạn có thể chứng minh normalized dataset được derive từ đâu.

**Severity cần xử lý đặc biệt.** Checkov cho phép severity-based filtering khi dùng platform integration; tài liệu cũng nói \--skip-download sẽ loại các severity và một số enrichment khỏi output, còn severity filtering yêu cầu platform integration/API key. [*\[11\]*](https://www.checkov.io/2.Basics/CLI%20Command%20Reference.html) Vì Pilot của bạn đã quan sát severity=None, cách an toàn nhất là:

scanner\_severity\_raw  
  	↓  
 GIỮ NGUYÊN  
 null vẫn là null

      	\+

 severity\_mapping\_v1.csv  
  	↓  
 study-defined severity\_class  
  	↓  
 severity\_numeric

Không làm:

Checkov severity \= None  
     	↓  
 tự điền HIGH  
     	↓  
 gọi đó là "Checkov severity"

severity\_mapping\_v1.csv nên có:

| Trường | Ý nghĩa |
| :---- | :---- |
| check\_id | Policy ID |
| severity\_class | INFO/LOW/MEDIUM/HIGH/CRITICAL/UNKNOWN |
| severity\_numeric | Ordinal đã freeze |
| mapping\_source | Nguồn của quyết định |
| rationale | Tại sao mapping như vậy |
| mapping\_version | Ví dụ severity-v1 |
| mapping\_date | Ngày freeze |
| review\_status | reviewed/unreviewed |

Nếu dùng numeric baseline, có thể chọn LOW=1, MEDIUM=2, HIGH=3, CRITICAL=4, nhưng **UNKNOWN phải có policy rõ ràng trước experiment**; không nên tùy tiện map UNKNOWN thành MEDIUM chỉ vì tiện.

## **Thiết kế định danh, schema và feature**

Đây là nơi tôi khuyến nghị sửa rõ hơn so với tài liệu hiện tại: family\_id không chỉ nên đại diện “hai context variants giống nhau”, mà nên đại diện **lineage/task đủ gần để có nguy cơ leakage**.

Một hierarchy hợp lý là:

source\_id  
    ↓  
 source\_task\_id  
    ↓  
 family\_id  
    ↓  
 artifact\_id  
    ↓  
 scenario\_id  
    ↓  
 finding\_id

**source\_id** chỉ benchmark/repository gốc, ví dụ geniac\_secbench.

**source\_task\_id** giữ ID task/scenario từ upstream.

**family\_id** là grouping dùng cho split. Cách định nghĩa bảo thủ nên là: mọi artifact cùng một base infrastructure intent/task, cùng controlled base Terraform hoặc cùng lineage gần nhau phải ở cùng family. Tất cả Context A/B chắc chắn cùng family\_id.

Ví dụ:

family\_id \= F0023

 ├── artifact A generated by model X  
 │   ├── scenario F0023-A1-DEV  
 │   └── scenario F0023-A1-PROD  
 │  
 └── artifact B generated from same upstream task  
 	├── scenario F0023-A2-DEV  
 	└── scenario F0023-A2-PROD

Nếu hai LLM sinh hai file khác nhau nhưng từ **cùng một benchmark task**, cách an toàn nhất là vẫn để cùng family. Điều này làm số family nhỏ hơn nhưng chống leakage tốt hơn. Không nên định nghĩa family chỉ bằng file hash, vì hai Terraform có cấu trúc gần như giống nhau nhưng đổi whitespace/naming vẫn có hash khác.

**artifact\_id** đại diện một output kỹ thuật cụ thể.

**scenario\_id** đại diện một artifact trong một contextual condition, ví dụ:

F0023-A1-C0  
 F0023-A1-C1

trong đó C0/C1 là low-/high-risk context.

**finding\_id** phải unique trong toàn dataset. Nên derive từ:

scenario\_id  
 \+  
 check\_id  
 \+  
 normalized\_resource\_address  
 \+  
 occurrence\_index

Ngoài ra cần một logical\_finding\_key riêng:

logical\_finding\_key \=  
 check\_id \+ normalized\_resource\_address

để match cùng finding giữa Context A và B trong Experiment B2, đúng tinh thần protocol. fileciteturn0file0

Schema final nên rộng hơn schema Step 13 một chút để provenance và reproducibility không phải nằm rải rác ở nhiều nơi.

**Dataset schema đề xuất:**

| Nhóm | Trường chính | Bắt buộc? |
| :---- | :---- | ----: |
| Identity | dataset\_version, family\_id, artifact\_id, scenario\_id, finding\_id | Có |
| Upstream provenance | source\_id, source\_task\_id, source\_revision, source\_path | Có |
| Integrity | artifact\_sha256 | Có |
| Legal | license\_id, redistribution\_status | Có |
| Terraform | terraform\_version, provider\_version, validation\_status, validation\_log\_path | Có |
| Scanner | checkov\_version, scan\_id, raw\_scan\_path | Có |
| Finding | check\_id, check\_name, category | Có |
| Resource | resource\_address\_raw, resource\_address\_norm, resource\_type | Có |
| Location | file\_path, start\_line, end\_line | Nên có |
| Raw severity | scanner\_severity\_raw | Có, null được |
| Frozen severity | severity\_class, severity\_numeric, severity\_mapping\_version | Có nếu baseline dùng severity |
| Scenario context | environment, asset\_criticality, data\_sensitivity | Có |
| Finding context | internet\_exposure, privilege\_impact, reachability | Có |
| Optional facts | public\_access, wildcard\_action, wildcard\_resource, encryption\_missing, logging\_missing, resource\_role | Khi có evidence |
| Feature evidence | evidence\_ref, extraction\_method, unknown\_reason | Rất nên có |
| Ground truth | human\_rank, annotator\_id, rationale, rubric\_version | Chỉ benchmark |
| Derived GT | relevance\_grade, priority\_target | Auto-generated |
| QA | duplicate\_flag, root\_cause\_group\_id, ndcg3\_eligible, ndcg5\_eligible | Nên có |
| Split | split\_version, fold\_id | Sau khi freeze |

Feature taxonomy vẫn nên giữ hai tầng như Protocol v2.3. fileciteturn0file0

**Scenario-level / business context:**

environment  
 asset\_criticality  
 data\_sensitivity

AWS Well-Architected coi data classification theo **criticality và sensitivity** là cơ sở để quyết định mức bảo vệ thích hợp; do đó hai dimensions này có cơ sở security/operational rõ ràng, không phải feature tùy ý. [*\[12\]*](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/data-classification.html)

Ví dụ metadata:

context\_id: C1  
 environment: production  
 asset\_criticality: high  
 data\_sensitivity: high

Những biến này phải đến từ scenario metadata, không được suy ra:

resource\_name \= "payment-prod-db"  
     	↓  
 environment \= production  
 data\_sensitivity \= high

Nếu metadata không có thì để UNKNOWN, không “đoán thông minh”.

**Finding/resource-level context:**

internet\_exposure  
 reachability  
 privilege\_impact

cộng với optional infrastructure facts:

public\_access  
 wildcard\_action  
 wildcard\_resource  
 encryption\_missing  
 logging\_missing  
 resource\_role

AWS Well-Architected nhấn mạnh least privilege, hạn chế overly permissive policies và tránh public access không cần thiết; đây là cơ sở tốt cho privilege\_impact, wildcard\_\* và public\_access. [*\[13\]*](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/sec_permissions_least_privileges.html)

Feature extraction phải theo nguyên tắc **evidence-first**:

Terraform / scanner evidence  
        	↓  
 Deterministic extraction rule  
        	↓  
 Feature value

không phải:

Security intuition  
  	↓  
 Feature value

Ví dụ:

| Feature | Giá trị | Evidence hợp lệ |
| :---- | ----: | :---- |
| internet\_exposure | 1 | CIDR/public configuration cho phép direct Internet exposure |
| internet\_exposure | 0 | Có evidence rõ không public |
| reachability | 1 | Resource path/config cho thấy trực tiếp reachable theo definition đã freeze |
| reachability | UNKNOWN | Không đủ thông tin để kết luận |
| wildcard\_action | 1 | IAM Action="\*" hoặc equivalent |
| wildcard\_resource | 1 | IAM Resource="\*" |
| encryption\_missing | 1 | Required/configurable encryption absent theo rule đã freeze |
| logging\_missing | 1 | Relevant logging control absent |
| privilege\_impact | 0–3 | Chỉ từ IAM/permission evidence |

privilege\_impact theo v2.3 có thể dùng:

0 \= no privilege implication  
 1 \= broad/indirect permission implication  
 2 \= privilege expansion / permission-management implication  
 3 \= unrestricted administrative or IAM control

fileciteturn0file0

Với những feature phức tạp như reachability, **đừng cố xây attack graph**. Nếu việc xác định cần suy luận topology quá sâu, dùng UNKNOWN. Out-of-scope firewall của v2.3 đã đúng khi loại attack graph khỏi luận văn. fileciteturn0file0

Tôi khuyến nghị mỗi feature có một feature\_definition.md hoặc machine-readable registry:

feature\_name  
 type  
 allowed\_values  
 definition  
 positive\_evidence  
 negative\_evidence  
 unknown\_rule  
 extraction\_method  
 version

Ví dụ:

internet\_exposure

 Type:  
 binary \+ unknown

 1:  
 explicit direct Internet exposure evidenced by Terraform

 0:  
 explicitly non-public / internal based on frozen rule

 UNKNOWN:  
 evidence insufficient

 Forbidden:  
 infer from resource name  
 infer from human rank  
 infer from ML prediction

**Feature-freeze checkpoints** nên là:

Scanner findings frozen  
     	↓  
 Normalization schema frozen  
     	↓  
 Feature definitions frozen  
     	↓  
 Feature extraction completed  
     	↓  
 Feature QA  
     	↓  
 ONLY THEN  
 Human annotation

Protocol v2.3 yêu cầu objective features phải được tạo **trước annotation**, chính xác để chống target leakage. fileciteturn0file0

Tôi khuyến nghị thêm bốn artifact freeze rõ ràng:

docs/normalization\_schema\_v1.md  
 docs/feature\_definitions\_v1.md  
 docs/severity\_mapping\_v1.md  
 docs/annotation\_rubric\_v1.md

Mỗi lần thay đổi sau freeze phải tạo v2 hoặc methodology amendment; không overwrite file cũ.

## **Ground truth và giao thức annotation**

Ground truth của luận văn phải được định nghĩa rất cẩn thận:

**Ground truth \= relative contextual remediation priority of scanner findings within a scenario under the study's predefined annotation protocol.**

Không được gọi nó là:

“true real-world cyber risk”.

Protocol v2.3 cũng giữ đúng ranh giới này: đơn vị ranking là **một scanner finding trong một scenario**, mỗi finding có một unique rank. fileciteturn0file0

Rubric không nên là một công thức kiểu:

Production \= \+3  
 Sensitive \= \+3  
 Public \= \+3  
 IAM \= \+3

vì nếu Random Forest lại nhận đúng các feature đó, model sẽ chỉ học lại arithmetic formula. Blueprint của bạn đã nhận diện đây là construct circularity. fileciteturn0file2

Thay vào đó, rubric nên là **decision framework** giúp annotator reason nhất quán, không tự động sinh rank.

**Annotation rubric đề xuất:**

| Dimension | Câu hỏi annotator cần xét | Evidence chính | Vai trò |
| :---- | :---- | :---- | :---- |
| Exposure / Reachability | Issue có trực tiếp làm resource dễ tiếp cận từ untrusted network không? | Terraform/network facts | Tăng urgency khi exposure có ý nghĩa |
| Privilege | Issue có tạo broad/admin/permission-management capability không? | IAM policy/resource | Đánh giá blast potential mà không cần attack graph |
| Data sensitivity | Resource xử lý/lưu dữ liệu nhạy cảm đến mức nào? | Explicit scenario metadata | Contextual impact |
| Asset criticality | Resource quan trọng với workload/business đến mức nào? | Explicit metadata | Contextual impact |
| Environment | Dev/staging/prod có làm urgency thay đổi không? | Explicit metadata | Operational context |
| Security control gap | Encryption/logging/access control nào bị thiếu? | Terraform/finding evidence | Phân biệt preventive/detective gaps |
| Impact reasoning | Confidentiality/Integrity/Availability nào có khả năng bị ảnh hưởng? | Evidence tổng hợp | Tie-break/supporting reasoning |
| Evidence confidence | Có đủ dữ liệu để kết luận không? | Code \+ structured evidence | Không được đoán |

Các khái niệm này phù hợp với AWS guidance về sensitivity/criticality, least privilege và public-access control. CVSS v4 Environmental metrics cũng cho phép điều chỉnh assessment dựa trên tầm quan trọng của asset và local security requirements; tuy nhiên CVSS không nên được biến thành ground truth trực tiếp cho Terraform scanner findings. [*\[14\]*](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/data-classification.html)

Một **annotation packet** cho mỗi scenario nên chứa:

scenario\_id  
 business context

 all in-scope findings:  
 	finding\_id  
 	check\_id  
 	check\_name  
 	resource  
 	relevant source-code excerpt/reference  
 	objective infrastructure features

và **không chứa**:

severity-based predicted rank  
 deterministic baseline score/rank  
 Random Forest score/rank  
 XGBoost score/rank  
 NDCG  
 Spearman  
 feature importance  
 previous annotator ranking

Đây đúng với protocol hiện tại. fileciteturn0file0

Tôi còn khuyến nghị **ẩn severity\_class/severity\_numeric khỏi annotation packet** nếu có thể. Annotator vẫn nhìn check\_id, check\_name và technical evidence để hiểu issue, nhưng không bị một nhãn HIGH/LOW anchor quyết định. Việc này làm ground truth độc lập hơn với Severity-only baseline.

Quy trình cho từng scenario:

Đọc business context  
     	↓  
 Đọc toàn bộ findings  
     	↓  
 Xem objective features  
     	↓  
 Mở Terraform source khi cần  
     	↓  
 So sánh findings với nhau  
     	↓  
 Rank 1 ... N, không tie  
     	↓  
 Ghi rationale  
     	↓  
 Submit

Protocol yêu cầu annotator đọc toàn bộ findings, resource, technical facts, Terraform khi cần, context, sau đó rank và ghi rationale. fileciteturn0file0

**Rationale capture** nên có cả structured field và free text:

| Trường | Ví dụ |
| :---- | :---- |
| primary\_driver | PUBLIC\_EXPOSURE |
| secondary\_driver | SENSITIVE\_DATA |
| confidence | HIGH |
| rationale | Public-facing production datastore containing high-sensitivity data; missing control raises direct exposure consequence. |
| evidence\_refs | main.tf:44-63 |

Structured drivers giúp sau này QA dễ hơn, nhưng **không được tự động chuyển chúng thành label**.

Nếu có hai findings gần như cùng root cause, vẫn giữ finding-level ranking theo protocol, nhưng nên thêm:

root\_cause\_group\_id

để thesis có thể nói rõ chúng phụ thuộc nhau. Protocol v2.3 đã yêu cầu không gọi nhiều scanner findings cùng một configuration problem là các vulnerability độc lập. fileciteturn0file0

Về annotator, với hoàn cảnh một sinh viên:

**Khuyến nghị chính: A1 annotate toàn benchmark \+ A2 annotate subset.**

Nếu có GVHD, giảng viên security hoặc practitioner hỗ trợ, chỉ cần A2 annotate khoảng **10–20% benchmark theo stratified selection** cũng đã có giá trị hơn việc cố bắt A2 làm toàn bộ dataset rồi bị tắc tiến độ. A1 và A2 phải annotate độc lập, không xem rank của nhau trước khi hoàn thành subset.

Nếu chỉ có A1, v2.3 cho phép:

A1 full annotation  
 \+  
 self-retest một subset

nhưng phải gọi đúng là **intra-rater/self-consistency check**, không được gọi là inter-annotator agreement. fileciteturn0file0

Tôi khuyến nghị self-retest khoảng 10–15% scenario sau ít nhất một khoảng nghỉ đủ để giảm nhớ ranking trước đó, và báo cáo rank correlation/descriptive consistency. Không thay đổi final ground truth chỉ vì thấy model dự đoán khác.

Trước annotation chính, có thể dùng **3–5 pilot scenarios không thuộc final test set** để calibrate rubric:

Annotate pilot  
  	↓  
 Phát hiện rubric ambiguity  
  	↓  
 Sửa rubric  
  	↓  
 FREEZE rubric  
  	↓  
 Main annotation

Sau khi main annotation bắt đầu, không tiếp tục sửa rubric trừ khi có methodology amendment.

**Rank → NDCG relevance** phải giữ đúng v2.3:

| Human rank | Relevance |
| ----: | ----: |
| 1 | 3 |
| 2 | 2 |
| 3 | 1 |
| 4+ | 0 |

fileciteturn0file0

Annotator **không nhập relevance**. Script derive tự động từ rank. Đây là điểm quan trọng để giảm manual error.

Scikit-learn định nghĩa NDCG bằng cách xếp các true relevance theo predicted scores, áp dụng logarithmic discount rồi chuẩn hóa theo ideal DCG; score cao khi các item có relevance cao được đưa lên đầu. [*\[5\]*](https://scikit-learn.org/dev/modules/generated/sklearn.metrics.ndcg_score.html) Với mapping trên, NDCG chủ yếu quan tâm top-3, còn NDCG@5 xem chất lượng top-5 nhưng rank 4+ đều relevance 0\. Điều này phù hợp nếu research construct của bạn là **ưu tiên top remediation items**, chứ không phải tái tạo chính xác toàn bộ thứ tự từ 1 đến N.

Điểm methodology còn thiếu cần freeze là **Random Forest target**. RandomForestRegressor cần numerical regression target. [*\[15\]*](https://scikit-learn.org/1.6/modules/generated/sklearn.ensemble.RandomForestRegressor.html) Tôi khuyến nghị:

Canonical Ground Truth:  
 human\_rank

 Evaluation Ground Truth:  
 relevance\_grade \= {3,2,1,0}

 ML training target:  
 priority\_target\_norm

với:

Ví dụ scenario 5 findings:

| Rank | Training target | NDCG relevance |
| ----: | ----: | ----: |
| 1 | 1.00 | 3 |
| 2 | 0.75 | 2 |
| 3 | 0.50 | 1 |
| 4 | 0.25 | 0 |
| 5 | 0.00 | 0 |

Ưu điểm là model vẫn học distinction giữa rank 4 và 5, nhưng NDCG evaluation vẫn giữ definition đã freeze. Đây là **đề xuất bổ sung**, cần ghi rõ vào protocol trước Step training.

## **Split, leakage, mất cân bằng và augmentation**

**Nguy cơ leakage lớn nhất không phải finding bị duplicate y hệt, mà là cùng infrastructure intent xuất hiện ở train và test dưới hình thức khác nhau.**

Ví dụ sai:

Family F01

 same base Terraform  
 ├── DEV  → TRAIN  
 └── PROD → TEST

Model đã nhìn gần như toàn bộ technical structure của test sample trong train.

Protocol v2.3 chính xác khi cấm finding-level random split và yêu cầu family-based split. fileciteturn0file0

Scikit-learn GroupKFold đảm bảo các group không overlap giữa train/test folds và mỗi group xuất hiện một lần ở test qua các fold. [*\[16\]*](https://scikit-learn.org/dev/modules/generated/sklearn.model_selection.GroupKFold.html) Với dataset nhỏ, đây phù hợp hơn random KFold.

Ba chiến lược có thể cân nhắc:

| Chiến lược | Ưu điểm | Nhược điểm | Khuyến nghị |
| :---- | :---- | :---- | :---- |
| Fixed family train/val/test | Dễ giải thích, dễ demo | Kết quả phụ thuộc một split | Tốt cho final holdout |
| GroupKFold | Tận dụng data tốt hơn, không overlap family | Nhiều lần train | **Khuyến nghị primary CV** |
| Leave-One-Family-Out | Leakage protection mạnh, tận dụng data tối đa | Nhiều folds, variance cao | Tốt nếu family count rất nhỏ |

Tôi khuyến nghị cấu trúc:

FULL FROZEN BENCHMARK  
       	↓  
 Family-level holdout test \~20%  
       	↓  
 Remaining families  
       	↓  
 GroupKFold for model selection / development

nhưng nếu dataset chỉ khoảng 18–20 families thì một fixed 20% test sẽ rất nhỏ. Khi đó **GroupKFold làm primary evaluation** có thể hợp lý hơn. Điều quan trọng là chọn **một protocol chính trước khi xem result**.

**Split plan deliverable** nên như sau:

| Trường | Quy định |
| :---- | :---- |
| group\_key | family\_id |
| Same family across splits | Cấm |
| Same context pair across splits | Cấm |
| Exact duplicate across splits | Cấm |
| Near-duplicate/source-task variants | Cùng family |
| Main CV | GroupKFold, số folds freeze trước run |
| Optional small-data CV | Leave-One-Family-Out |
| Random seed | Freeze |
| Split manifest | Lưu family IDs của mọi fold |
| Test use | Không dùng để chỉnh feature/rubric/baseline |

**Leakage QA** cần có một assert rất đơn giản:

set(train.family\_id)  
 ∩  
 set(test.family\_id)  
 \=  
 ∅

và nếu có validation:

train ∩ validation \= ∅  
 train ∩ test   	\= ∅  
 validation ∩ test  \= ∅

Ngoài family leakage còn ba dạng leakage khác.

**Target leakage:** tạo feature dựa trên human rank.

human rank  
    ↓  
 "risk\_feature"  
    ↓  
 model

Cấm.

**Construct leakage/circularity:** annotator dùng một deterministic formula từ public, prod, sensitive, rồi model được train bằng chính các feature đó. Đây không phải software leakage nhưng làm kết luận “ML learned risk” yếu. Blueprint đã cảnh báo vấn đề này. fileciteturn0file2 Cách giảm: rubric là reasoning framework, không là formula; làm feature ablation; kết luận khiêm tốn rằng model học **study-defined contextual priority**.

**Identity leakage:** check\_id, scenario\_id, file path hoặc resource name vô tình cho model biết finding family/rank pattern. scenario\_id, family\_id, finding\_id, source path tuyệt đối không được đưa vào ML features. check\_id chỉ nên dùng trong optional ablation hoặc có justification rõ. v2.3 cũng cảnh báo model không nên chỉ học mapping check\_id → rank. fileciteturn0file0

Về **class imbalance**, bài toán chính của bạn là regression/ranking nên không có “class imbalance” theo nghĩa classification thông thường. Tuy nhiên có ba dạng skew:

Relevance skew:  
 rank 4+ đều relevance 0

 Category skew:  
 logging findings có thể nhiều hơn IAM/public access

 Scenario-size skew:  
 scenario 12 findings đóng góp 12 samples  
 scenario 3 findings chỉ đóng góp 3 samples

Không nên dùng SMOTE để tạo fake security findings hoặc synthetic priority labels.

Đặc biệt:

NO:  
 SMOTE findings  
 synthetic human ranks  
 LLM-generated priority labels  
 copy finding từ family A sang B  
 random oversampling trước family split

Synthetic labels sẽ làm mất ý nghĩa của human ground truth.

Cách xử lý tốt hơn:

**Trước benchmark freeze:** sampling thêm **families** chứa category/resource hiếm theo selection rules đã định nghĩa.

**Trong evaluation:** metric tính ở scenario level nên một scenario lớn không được xem như 15 independent experiments.

**Trong training:** có thể cân nhắc sample weighting để mỗi scenario có tổng weight xấp xỉ nhau:

RandomForestRegressor hỗ trợ sample\_weight khi fit. [*\[17\]*](https://scikit-learn.org/dev/modules/generated/sklearn.ensemble.RandomForestRegressor.html) Đây là optional refinement; với người lần đầu ML, tôi sẽ **chỉ dùng nếu scenario-size distribution lệch mạnh**. Nếu không, giữ model đơn giản.

Data augmentation được phép ở dạng:

New real/public artifact  
 \+  
 passes frozen inclusion rules  
 \+  
 added BEFORE benchmark freeze

hoặc controlled context A/B:

same technical artifact  
 \+  
 explicit different business context

nhưng context variant **không tạo label tự động**; mỗi scenario vẫn phải được human annotate.

Không được augmentation sau khi thấy:

RF NDCG thấp  
     	↓  
 thêm scenario "dễ"

vì đó là metric-driven dataset modification, v2.3 đã cấm. fileciteturn0file0

## **QA, reproducibility, pháp lý và deliverables**

Dataset nên có ba trạng thái vật lý tách biệt:

data/raw/  
 	immutable upstream artifacts  
 	raw Checkov JSON

 data/interim/  
 	validation outputs  
 	normalized findings  
 	extracted features

 data/frozen/  
 	benchmark\_v1/  
 	annotations\_v1/  
 	splits\_v1/

Không chỉnh trực tiếp raw data.

Một repository tối giản:

dataset/  
 ├── source\_inventory/  
 │   └── provenance\_v1.csv  
 │  
 ├── raw/  
 │   ├── terraform/  
 │   ├── checkov/  
 │   └── validation/  
 │  
 ├── normalized/  
 │   └── findings\_v1.csv  
 │  
 ├── features/  
 │   └── finding\_context\_features\_v1.csv  
 │  
 ├── contexts/  
 │   └── scenarios\_v1.yaml  
 │  
 ├── annotations/  
 │   ├── annotation\_A1\_v1.csv  
 │   └── annotation\_A2\_subset\_v1.csv  
 │  
 ├── frozen/  
 │   └── prioritization\_benchmark\_v1.csv  
 │  
 └── manifests/  
 	├── tool\_versions.json  
 	├── hashes.csv  
 	└── splits\_v1.json

DVC/database không bắt buộc. Với một sinh viên, Git \+ file manifest \+ immutable hashes \+ release archive là đủ nếu dataset không quá lớn.

**Provenance table** nên là deliverable chính thức:

| Field | Ví dụ / ý nghĩa |
| :---- | :---- |
| source\_id | geniac\_secbench |
| source\_revision | commit/revision cụ thể |
| source\_task\_id | upstream scenario |
| source\_artifact\_path | path upstream |
| generator\_model | nếu known |
| prompt/condition\_id | nếu known |
| artifact\_sha256 | integrity |
| retrieval\_date | ngày tải |
| license\_id | CC-BY-4.0/MIT/... |
| redistribution\_status | allowed/reference-only/unknown |
| citation\_key | paper/dataset citation |
| family\_id | grouping nội bộ |
| notes | adaptation/exclusion info |

“Public trên GitHub/Hugging Face” **không đồng nghĩa với được phép redistribute theo mọi cách**. GenIaC-SecBench chẳng hạn ghi rõ project-produced data là CC-BY-4.0, nhưng human\_reference\_dataset giữ license gốc của từng upstream repository. [*\[6\]*](https://huggingface.co/datasets/AnimeshShaw/GenIaC-SecBench) IaC-Eval repository ghi MIT. [*\[3\]*](https://github.com/autoiac-project/iac-eval) IaCSecBench cũng ghi MIT và cố ý không vendor một số third-party sources mà chỉ pin external repositories. [*\[18\]*](https://github.com/mchittineni/iacsecbench)

Do đó legal workflow:

Artifact candidate  
   	↓  
 Identify upstream  
   	↓  
 Record license  
   	↓  
 Can redistribute?  
   ┌───┴────┐  
  yes       unclear/no  
   │           │  
 store   	metadata/reference  
 artifact	only or exclude

Với Security-First Text-to-Terraform, paper nói artifacts công khai, nhưng “publicly available” không tự nó xác nhận quyền redistribute; cần kiểm tra license trong artifact repository trước khi copy vào release package. [*\[2\]*](https://arxiv.org/abs/2608.02672)

Về ethics/security, không chạy terraform apply trên untrusted public IaC. terraform validate không kiểm tra remote services và có thể chạy tự động sau initialization; đây phù hợp với static research design của bạn. [*\[7\]*](https://developer.hashicorp.com/terraform/cli/commands/validate) Tốt nhất chạy acquisition/validation/scanning trong container hoặc isolated environment **không có AWS credentials**. Nếu upstream artifact vô tình chứa secret, personal identifier hoặc sensitive endpoint, không đưa trực tiếp vào public thesis dataset; log và redact/exclude theo policy.

**Reproducibility manifest** tối thiểu phải giữ:

| Nhóm | Cần ghi |
| :---- | :---- |
| Terraform | CLI version |
| Providers | provider names/versions \+ lockfile/hash |
| Checkov | 3.3.17 \+ command flags |
| Python | version |
| ML | scikit-learn version |
| Dataset | dataset version |
| Code | Git commit SHA |
| Artifacts | SHA-256 |
| Features | feature schema version |
| Severity | mapping version |
| Annotation | rubric version |
| Ground truth | annotation version |
| Split | exact family/fold manifest |
| RF | random seed \+ hyperparameters |
| Outputs | predictions \+ metrics |
| Statistics | test configuration \+ bootstrap seed |

Checkov 3.3.17 có PyPI package và provenance attestation chính thức, do đó version này có thể freeze và tái tạo rõ ràng. [*\[9\]*](https://pypi.org/project/checkov/3.3.17/) Checkov cũng hỗ trợ JSON output, phù hợp với việc lưu raw scan artifact. [*\[19\]*](https://www.checkov.io/2.Basics/CLI%20Command%20Reference.html)

**QA checklist cho dataset freeze** nên chạy bằng script, không chỉ kiểm bằng mắt:

| QA check | Điều kiện PASS |
| :---- | :---- |
| Provenance completeness | Mọi artifact có source/revision/license |
| Integrity | Mọi artifact có SHA-256 |
| Terraform validity | Research-corpus artifact PASS theo policy |
| Scanner consistency | Cùng Checkov version/flags |
| Raw preservation | Raw JSON tồn tại |
| Normalization consistency | Raw failed findings đối chiếu được với normalized records |
| ID uniqueness | finding\_id không duplicate |
| Family consistency | Context variants cùng family |
| Exact duplicate | Không nằm dưới nhiều family IDs |
| Context completeness | Không missing silent values |
| Feature domains | Chỉ accepted values |
| Unknown handling | Unknown có lý do, không đoán |
| Annotation completeness | Mọi in-scope finding có rank/rationale |
| Rank uniqueness | Rank \= 1..N, không thiếu/duplicate |
| Relevance | Auto-derived đúng mapping |
| NDCG eligibility | Count scenario ≥3/≥5 |
| Split leakage | Family intersections \= ∅ |
| Severity mapping | Mọi mapped severity truy được mapping version |
| Post-freeze integrity | Không edit data không version |

**Annotation deliverable** nên có schema riêng:

| Field | Người nhập hay tự động? |
| :---- | :---- |
| scenario\_id | Auto |
| finding\_id | Auto |
| annotator\_id | Auto/config |
| human\_rank | Human |
| primary\_driver | Human |
| secondary\_driver | Human, optional |
| confidence | Human |
| rationale | Human |
| evidence\_refs | Human/assisted |
| annotation\_timestamp | Auto |
| rubric\_version | Auto |
| relevance\_grade | **Auto, không human nhập** |
| priority\_target\_norm | **Auto sau freeze** |

**Split-plan deliverable**:

| Fold | Families | Scenarios | Findings | NDCG@3 eligible | NDCG@5 eligible | Category coverage |
| :---- | ----: | ----: | ----: | ----: | ----: | :---- |
| Fold A | … | … | … | … | … | … |
| Fold B | … | … | … | … | … | … |
| Fold C | … | … | … | … | … | … |
| Fold D | … | … | … | … | … | … |
| Fold E | … | … | … | … | … | … |

Đừng chỉ báo “80/20 split”. Với thesis này, người đọc cần biết **bao nhiêu independent families** nằm ở mỗi fold.

## **Quy mô, lịch triển khai, rủi ro và checklist**

Protocol v2.3 hiện đặt target **40–60 base families, 80–120 contextual scenarios, ≥300 findings preferred**, nhưng chính protocol nhấn mạnh đây là planning target và NDCG@5 eligibility/category/resource/family diversity quan trọng hơn raw count. fileciteturn0file0 Với một người lần đầu làm ML, tôi sẽ không dùng con số đó làm graduation criterion.

**So sánh quy mô:**

| Mức | Families | Contextual scenarios | Annotated findings | NDCG@5 target | Đánh giá |
| :---- | ----: | ----: | ----: | ----: | :---- |
| Pilot hiện có | \~5 pairs / 10 scenarios | 10 | Pilot có 118 raw failed findings | 8/10 readiness trong pilot | Chỉ feasibility |
| **Minimum defensible** | **18–24** | **36–48** | **150–250** | Cố gắng ≥15–20 valid scenarios | Có thể bảo vệ nếu diversity/QA tốt |
| **Recommended cho bạn** | **24–36** | **48–72** | **250–400** | Khoảng 25–35+ nếu corpus cho phép | Cân bằng tốt giữa science và workload |
| Protocol target | 40–60 | 80–120 | ≥300 preferred | Ưu tiên cao | Tốt nếu acquisition/annotation chạy thuận lợi |
| Quá lớn đối với scope hiện tại | 60+ | 120+ | 600–1000+ | Cao | Annotation workload dễ phá timeline |

Mức “minimum/recommended” ở trên là **khuyến nghị quản trị scope của báo cáo này**, không phải ngưỡng thống kê được chứng minh. Blueprint ban đầu chỉ đặt target khoảng 15–20 valid paired scenarios nếu dataset cho phép, và v2.3 chủ động tránh hard requirement về raw count. fileciteturn0file2 fileciteturn0file0

Có một lý do thực tế để không săn số lượng: 300 findings nhưng đến từ 10 family rất giống nhau kém giá trị hơn 250 findings đến từ 30 family độc lập và nhiều resource/security categories.

Nguyên tắc ưu tiên:

Family diversity  
   	\+  
 Ground-truth quality  
   	\+  
 NDCG eligibility  
   	\+  
 Category/resource coverage  
   	\+  
 No leakage  
   	\>  
 Raw number of findings

Với tổng thời gian tối đa khoảng ba tháng nhưng phải giữ tối thiểu hai tuần buffer, bạn nên coi **8 tuần đầu là research/implementation window**, phù hợp chính Blueprint và Amendment hiện tại. fileciteturn0file0 fileciteturn0file2 Dataset \+ annotation **phải freeze lý tưởng cuối tuần 4, chậm nhất cuối tuần 5**; nếu kéo tới tuần 7 thì ML/evaluation/report sẽ bị ép quá mạnh.

**Timeline đề xuất cho Dataset & Ground Truth:**

| Tuần | Công việc | Deliverable bắt buộc | Kill/Pivot rule |
| :---- | :---- | :---- | :---- |
| **Week 1** | Source inventory; license/provenance; download candidates; định nghĩa family\_id | provenance\_v1.csv, source corpus | Không rõ license → reference-only/exclude |
| **Week 2** | terraform init \-backend=false; validate; Checkov 3.3.17; raw retention; exclusion logs | Research Corpus v1 \+ raw scans | Dependency quá phức tạp → loại theo frozen rule |
| **Week 3** | Normalize; deduplicate; family QA; severity mapping; feature extraction; benchmark stratification | findings\_v1.csv, features\_v1.csv, severity\_mapping\_v1 | Không đủ ≥5-finding scenarios → mở rộng corpus theo predefined rule |
| **Week 4** | Context A/B; annotation calibration; main A1 annotation; rationale QA | Ground Truth v1 | Nếu annotation workload vượt khả năng → giảm số families, không truncate findings |
| **Week 5 contingency** | Finish A1; A2 subset/self-retest; final QA; rank→relevance; split freeze | Benchmark v1 \+ annotation freeze \+ split manifest | **Hard freeze dataset** |
| Week 6 | Severity/context baseline \+ Random Forest | Không mở dataset lại |   |
| Week 7 | Evaluation/statistics/B2 | Results |   |
| Week 8 | Rerun, artifacts, figures, thesis package | Research freeze |   |
| Sau đó | Writing, fixes, demo, defense | Buffer | Không thêm feature |

Đây gần với timeline v2.3 vốn đặt acquisition ở Week 1, validation/scanning ở Week 2, feature/context ở Week 3, annotation ở Week 4, rồi baseline/ML/evaluation từ Week 5 trở đi. fileciteturn0file0

**Các rủi ro lớn nhất và mitigation:**

| Rủi ro | Mức | Dấu hiệu | Mitigation |
| :---- | ----: | :---- | :---- |
| Ground truth chủ quan | Rất cao | Khó giải thích rank | Rubric \+ rationale \+ A2 subset/self-retest |
| Circularity | Rất cao | ML gần như tái tạo rule formula | Không dùng formula tạo GT; ablation; claim hạn chế |
| Family leakage | Rất cao | Metric quá đẹp | Conservative family grouping \+ GroupKFold |
| Annotation overload | Rất cao | Week 4 chưa qua 50% | Giảm families trước freeze, không giảm rationale |
| Severity ambiguity | Cao | None/UNKNOWN nhiều | Raw severity riêng \+ frozen mapping |
| Near duplicates | Cao | Nhiều artifacts từ cùng task/model | Group cùng source task/family |
| Dataset source bias | Cao | Một benchmark \>80% benchmark | Stratified source sampling |
| Category skew | Trung bình–cao | 60% findings cùng category | Add families by frozen coverage rule |
| Small effective sample | Cao | Nhiều findings nhưng ít families | Báo family/scenario counts, không chỉ rows |
| License problem | Trung bình | Public artifact không có license | Metadata-only/reference/exclude |
| Feature guessing | Cao | Nhiều manual assumptions | UNKNOWN thay vì đoán |
| Model underperforms | **Không phải failure** | RF ≈/kém rule | Report negative result đúng protocol |

Điểm cuối rất quan trọng: **RF không thắng Context Rule không phải rủi ro methodology.** Nó chỉ trở thành vấn đề nếu dataset/ground truth không đáng tin. Protocol của bạn đã đúng khi cho phép negative result. fileciteturn0file0

Checklist ưu tiên cụ thể từ thời điểm này:

| Priority | Việc cần làm ngay | Output |
| :---- | :---- | :---- |
| **P0** | Freeze định nghĩa family\_id, artifact\_id, scenario\_id, finding\_id | docs/id\_schema\_v1.md |
| **P0** | Freeze admission/exclusion rules trước acquisition chính | docs/dataset\_admission\_v1.md |
| **P0** | Lập inventory GenIaC-SecBench, Security-First, IaC-Eval, IaCSecBench | provenance\_v1.csv |
| **P0** | Pin Terraform/provider/Checkov 3.3.17 và scan flags | tool\_versions.json |
| **P0** | Giữ scanner\_severity\_raw riêng; xây severity mapping policy | severity\_mapping\_v1.md/csv |
| **P0** | Freeze normalization schema | normalized\_schema\_v1.md |
| **P0** | Freeze feature definitions \+ evidence rules | feature\_definitions\_v1.md |
| **P0** | Chạy acquisition → validate → scan → normalize toàn candidate corpus | Research Corpus v1 |
| **P1** | Thống kê finding density/category/resource/source/family | corpus\_summary\_v1 |
| **P1** | Freeze stratified benchmark selection rule | benchmark\_selection\_v1.md |
| **P1** | Chọn \~24–36 families nếu corpus cho phép | Benchmark candidates |
| **P1** | Tạo Context A/B nhưng không tạo labels | context\_v1.yaml |
| **P1** | Calibration annotation 3–5 scenarios | Rubric corrections |
| **P1** | Freeze annotation rubric | annotation\_rubric\_v1.md |
| **P1** | A1 annotate toàn benchmark \+ rationale | annotation\_A1\_v1.csv |
| **P1** | A2 subset nếu có; nếu không self-retest subset | Agreement/consistency report |
| **P1** | Freeze human rank và auto-generate relevance | Ground Truth v1 |
| **P1** | Freeze ML target transform trước training | target\_definition\_v1.md |
| **P1** | Tạo family-based split/GroupKFold manifest | splits\_v1.json |
| **P1** | Chạy automated QA và lock benchmark | benchmark\_v1 |
| **P2** | Chỉ sau đó mới bắt đầu baseline/RF | Model-ready dataset |

**Definition of Done cho riêng Dataset & Ground Truth** nên là:

\[✓\] Source provenance complete  
 \[✓\] License status recorded  
 \[✓\] Raw Terraform archived/hashable  
 \[✓\] Terraform validation reproducible  
 \[✓\] Checkov version/flags frozen  
 \[✓\] Raw Checkov JSON retained  
 \[✓\] Findings normalized  
 \[✓\] Severity mapping frozen  
 \[✓\] Family IDs reviewed  
 \[✓\] Exact/near duplicates checked  
 \[✓\] Scenario contexts explicit  
 \[✓\] Feature definitions frozen  
 \[✓\] Feature evidence recorded  
 \[✓\] No features derived from labels  
 \[✓\] Benchmark selected without model results  
 \[✓\] Every in-scope finding annotated  
 \[✓\] Every rank has rationale  
 \[✓\] Rank unique and complete per scenario  
 \[✓\] Rank→relevance generated automatically  
 \[✓\] ML target definition frozen  
 \[✓\] NDCG@3/@5 eligibility reported  
 \[✓\] Family-level split verified  
 \[✓\] No family overlap across folds  
 \[✓\] Dataset version frozen  
 \[✓\] Final manifest \+ hashes stored

Đánh giá cuối cùng về Dataset & Ground Truth của đề tài là: **không cần dataset “rất lớn”; cần dataset có effective independence và annotation đáng tin.** Với thời gian của bạn, một benchmark **24–36 families / 48–72 scenarios / 250–400 findings được làm sạch, có provenance, evidence-based features, blind annotation, rationale và family-safe splits** sẽ mạnh hơn một benchmark 1.000 findings nhưng chỉ là nhiều biến thể từ vài task giống nhau.

Research story khi bảo vệ vì vậy nên được giữ cực kỳ rõ:

Public / prior-work GenAI Terraform  
           	↓  
   	Provenance Screening  
           	↓  
    Valid AWS Terraform Corpus  
           	↓  
     	Checkov 3.3.17  
           	↓  
  	Normalized Findings  
           	↓  
 Objective Infrastructure Facts  
           	\+  
 Explicit Business Context  
           	↓  
 	Blind Human Ranking  
           	↓  
   	Frozen Ground Truth  
           	↓  
 Family-safe Model Evaluation  
           	↓  
 Severity vs Context vs Random Forest

Điểm khoa học quan trọng nhất không phải **“em có bao nhiêu dòng dữ liệu”**, mà là:

**“Em có thể chứng minh từng dòng dữ liệu đến từ đâu, feature được tạo thế nào, label do ai quyết định, model chưa được nhìn thấy gì trước evaluation, và vì sao test set thực sự độc lập với train set hay không?”**

Nếu trả lời được năm câu đó một cách chặt chẽ, phần Dataset & Ground Truth sẽ trở thành một trong những điểm mạnh nhất của luận văn thay vì điểm yếu nhất.

---

[*\[1\]* *\[6\]*](https://huggingface.co/datasets/AnimeshShaw/GenIaC-SecBench) https://huggingface.co/datasets/AnimeshShaw/GenIaC-SecBench

[*https://huggingface.co/datasets/AnimeshShaw/GenIaC-SecBench*](https://huggingface.co/datasets/AnimeshShaw/GenIaC-SecBench)

[*\[2\]*](https://arxiv.org/abs/2608.02672) https://arxiv.org/abs/2608.02672

[*https://arxiv.org/abs/2608.02672*](https://arxiv.org/abs/2608.02672)

[*\[3\]*](https://github.com/autoiac-project/iac-eval) https://github.com/autoiac-project/iac-eval

[*https://github.com/autoiac-project/iac-eval*](https://github.com/autoiac-project/iac-eval)

[*\[4\]* *\[18\]*](https://github.com/mchittineni/iacsecbench) https://github.com/mchittineni/iacsecbench

[*https://github.com/mchittineni/iacsecbench*](https://github.com/mchittineni/iacsecbench)

[*\[5\]*](https://scikit-learn.org/dev/modules/generated/sklearn.metrics.ndcg_score.html) https://scikit-learn.org/dev/modules/generated/sklearn.metrics.ndcg\_score.html

[*https://scikit-learn.org/dev/modules/generated/sklearn.metrics.ndcg\_score.html*](https://scikit-learn.org/dev/modules/generated/sklearn.metrics.ndcg_score.html)

[*\[7\]*](https://developer.hashicorp.com/terraform/cli/commands/validate) https://developer.hashicorp.com/terraform/cli/commands/validate

[*https://developer.hashicorp.com/terraform/cli/commands/validate*](https://developer.hashicorp.com/terraform/cli/commands/validate)

[*\[8\]*](https://developer.hashicorp.com/terraform/tutorials/aws-get-started/aws-create) https://developer.hashicorp.com/terraform/tutorials/aws-get-started/aws-create

[*https://developer.hashicorp.com/terraform/tutorials/aws-get-started/aws-create*](https://developer.hashicorp.com/terraform/tutorials/aws-get-started/aws-create)

[*\[9\]*](https://pypi.org/project/checkov/3.3.17/) https://pypi.org/project/checkov/3.3.17/

[*https://pypi.org/project/checkov/3.3.17/*](https://pypi.org/project/checkov/3.3.17/)

[*\[10\]* *\[11\]* *\[19\]*](https://www.checkov.io/2.Basics/CLI%20Command%20Reference.html) https://www.checkov.io/2.Basics/CLI%20Command%20Reference.html

[*https://www.checkov.io/2.Basics/CLI%20Command%20Reference.html*](https://www.checkov.io/2.Basics/CLI%20Command%20Reference.html)

[*\[12\]* *\[14\]*](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/data-classification.html) https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/data-classification.html

[*https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/data-classification.html*](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/data-classification.html)

[*\[13\]*](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/sec_permissions_least_privileges.html) https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/sec\_permissions\_least\_privileges.html

[*https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/sec\_permissions\_least\_privileges.html*](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/sec_permissions_least_privileges.html)

[*\[15\]*](https://scikit-learn.org/1.6/modules/generated/sklearn.ensemble.RandomForestRegressor.html) https://scikit-learn.org/1.6/modules/generated/sklearn.ensemble.RandomForestRegressor.html

[*https://scikit-learn.org/1.6/modules/generated/sklearn.ensemble.RandomForestRegressor.html*](https://scikit-learn.org/1.6/modules/generated/sklearn.ensemble.RandomForestRegressor.html)

[*\[16\]*](https://scikit-learn.org/dev/modules/generated/sklearn.model_selection.GroupKFold.html) https://scikit-learn.org/dev/modules/generated/sklearn.model\_selection.GroupKFold.html

[*https://scikit-learn.org/dev/modules/generated/sklearn.model\_selection.GroupKFold.html*](https://scikit-learn.org/dev/modules/generated/sklearn.model_selection.GroupKFold.html)

[*\[17\]*](https://scikit-learn.org/dev/modules/generated/sklearn.ensemble.RandomForestRegressor.html) https://scikit-learn.org/dev/modules/generated/sklearn.ensemble.RandomForestRegressor.html

[*https://scikit-learn.org/dev/modules/generated/sklearn.ensemble.RandomForestRegressor.html*](https://scikit-learn.org/dev/modules/generated/sklearn.ensemble.RandomForestRegressor.html)

# Methodology & Experimental Design

# **Methodology & Experimental Design cho luận văn Context-Aware ML for Security Risk Prioritization of Generative-AI-Generated Terraform**

## **Tóm tắt điều hành**

Với điều kiện thực tế của bạn — **một sinh viên ngành Network & Security, thiên hướng DevSecOps, chưa học Machine Learning, tổng thời gian tối đa khoảng ba tháng nhưng phải giữ ít nhất hai tuần dự phòng** — thiết kế nghiên cứu nên được tối ưu theo nguyên tắc:

**Giảm độ phức tạp của Machine Learning, tăng độ chặt của dataset, ground truth và experimental design.**

Protocol v2.3 hiện tại đã đi đúng hướng khi chuyển từ việc tự xây toàn bộ benchmark sang chiến lược **reuse prior-work artifacts → security re-evaluation → context representation → human prioritization → ML comparison**; đồng thời giữ Random Forest là model bắt buộc, XGBoost chỉ optional, và cho phép single-annotator nếu được công bố rõ như một limitation. fileciteturn0file0 fileciteturn0file1

Sau khi đối chiếu protocol này với tài liệu chính thức của Checkov, Terraform, scikit-learn, SciPy và một số benchmark IaC/GenAI mới công bố, tôi khuyến nghị **không mở rộng methodology thêm model hoặc scanner**. Checkov đã hỗ trợ Terraform/plan scanning và JSON output; terraform validate kiểm tra tính hợp lệ cú pháp và nhất quán nội bộ chứ không kiểm tra remote services, vì vậy cặp terraform validate \+ Checkov phù hợp cho một pipeline static-analysis không cần triển khai AWS thật. [*\[1\]*](https://github.com/bridgecrewio/checkov?utm_source=chatgpt.com)

Thiết kế thực nghiệm nên xoay quanh ba so sánh:

| Phương pháp | Có severity | Có context | Có ML | Vai trò |
| :---- | ----: | ----: | ----: | :---- |
| Severity-only | ✓ | ✗ | ✗ | Baseline tối thiểu |
| Deterministic Context | ✓ | ✓ | ✗ | Kiểm tra giá trị của context |
| Random Forest | ✓ | ✓ | ✓ | Kiểm tra ML có thêm giá trị hay không |

Main research story vì vậy rất rõ:

Severity-only  
   	│  
   	│  RQ2  
   	▼  
 Context-aware Rule  
   	│  
   	│  RQ3  
   	▼  
 Random Forest

Thành công của luận văn **không được định nghĩa là Random Forest phải thắng**. V2.3 đã quy định negative result là hợp lệ và cấm điều chỉnh dataset hoặc annotation để làm hypothesis thành công. fileciteturn0file0

Đối với dataset, target 40–60 families / 80–120 contextual scenarios / ≥300 findings nên giữ đúng tư cách **planning target**, không biến thành hard requirement. Đây cũng chính là ngôn ngữ của Amendment v2.3. fileciteturn0file0 Với nguồn lực một người, tôi khuyến nghị thiết lập thêm một **contingency target**, nhưng không gọi đó là “sample size scientifically sufficient”: khoảng 25–40 families, đủ scenario có ít nhất 3 và đặc biệt ít nhất 5 findings để NDCG@3/@5 có ý nghĩa, và cố gắng đạt tối thiểu khoảng 15–20 paired scenarios cho các comparison chính như Blueprint trước đó dự kiến. Mức cuối cùng phải được báo cáo kèm confidence interval và limitation thay vì tuyên bố đủ power chỉ dựa trên số lượng. fileciteturn0file2

Điểm methodology tôi khuyến nghị **freeze ngay** là:

**Random Forest target nên được suy ra từ human rank bằng normalized priority, không train trực tiếp trên raw rank.**

Với scenario có N findings:

Như vậy:

Rank 1 → 1.00  
 ...  
 Rank N → 0.00

Điều này giữ toàn bộ thứ tự human ranking, nhưng tránh việc rank=5 mang ý nghĩa khác nhau giữa scenario có 5 findings và scenario có 12 findings. Ground-truth relevance dùng cho NDCG vẫn giữ nguyên protocol:

Rank 1 → 3  
 Rank 2 → 2  
 Rank 3 → 1  
 Rank 4+ → 0

Không được thay relevance mapping sau khi xem kết quả. fileciteturn0file0

Một quyết định khác nên freeze là:

**Không sử dụng check\_id trong main Random Forest experiment.**

check\_id là một shortcut rất mạnh: model có thể học rằng một rule ID thường xuyên được annotator xếp cao thay vì học tác động của context. Protocol v2.3 đã cảnh báo về mapping check\_id → rank. fileciteturn0file0 Hợp lý nhất là main model **không có check\_id**, sau đó thực hiện supplementary sensitivity run "with check\_id" để quan sát model performance thay đổi thế nào.

Cuối cùng, rủi ro khoa học lớn nhất của đề tài không phải là “Random Forest khó”, mà là **ground-truth circularity**:

Context features  
   	↓  
 Human uses same context  
 to create ranking  
   	↓  
 Random Forest receives  
 same context features  
   	↓  
 High NDCG

Một metric rất đẹp trong cấu trúc này chưa chứng minh model đã “khám phá real-world risk”; nó có thể chỉ chứng minh model học được **study-defined prioritization rubric**. Blueprint cũ của bạn đã nhận diện chính xác limitation này. fileciteturn0file2 Đây phải trở thành một threat-to-validity trung tâm của luận văn, không phải một footnote.

## **Thiết kế nghiên cứu và ánh xạ mục tiêu sang thí nghiệm**

### **Research construct cần freeze**

Thesis không nghiên cứu “real-world probability of compromise”. Construct được đo là:

**Contextual security-finding priority under the study's predefined methodology.**

Cách định nghĩa này phù hợp với protocol và tránh overclaim. fileciteturn0file0 Nó cũng phù hợp với tư duy của CVSS hiện đại: FIRST phân biệt intrinsic/base properties với các yếu tố Environmental riêng cho môi trường người dùng, đồng thời nói rõ CVSS chỉ là một input cho broader risk-management process chứ không phải toàn bộ risk assessment. [*\[2\]*](https://www.first.org/cvss/v4.0/specification-document?utm_source=chatgpt.com)

Do đó, luận văn nên tách ba lớp:

Technical Finding  
   	│  
   	▼  
 Objective Infrastructure Facts  
   	│  
   	▼  
 Business / Deployment Context  
   	│  
   	▼  
 Study-defined Human Priority

### **Mapping giữa objective, RQ và evidence**

| Mục tiêu | Câu hỏi nghiên cứu | Evidence chính | Experiment |
| :---- | :---- | :---- | :---- |
| Xác định misconfiguration quan sát được | RQ1 | Research Corpus | Characterization |
| Xác định context có giá trị không | RQ2 | Severity vs Context | B1 |
| Xác định ML có thêm giá trị không | RQ3 | Context Rule vs RF | B1 |
| Kiểm tra model phản ứng với context | Secondary | A/B matched findings | B2 |
| Hiểu model đang dựa vào feature nào | Exploratory | Importance / ablation | Exploratory |

Mapping này bám trực tiếp v2.3: RQ1 dùng research corpus lớn; RQ2 dùng Severity vs Context và hỗ trợ thêm bởi B2; RQ3 dùng Context Rule vs Random Forest; feature analysis chỉ là exploratory. fileciteturn0file0

### **Experimental pipeline cuối cùng**

flowchart TD  
     A\[Prior-work / GenAI Terraform artifacts\] \--\> B\[Provenance & license screening\]  
 	B \--\> C\[Terraform init \-backend=false \+ validate\]  
 	C \--\> D\[Checkov 3.3.17\]  
 	D \--\> E\[Raw Checkov JSON\]  
 	E \--\> F\[Finding normalization\]

 	F \--\> G\[Finding/resource feature extraction\]  
 	F \--\> H\[Scenario/business metadata\]

 	G \--\> I\[Feature table\]  
 	H \--\> I

 	I \--\> J\[Freeze feature schema\]  
 	J \--\> K\[Blind human annotation\]  
 	K \--\> L\[Human rank \+ rationale\]  
 	L \--\> M\[Derive normalized priority target\]  
 	L \--\> N\[Derive NDCG relevance 3/2/1/0\]

 	M \--\> O\[Family-based cross-validation\]

 	O \--\> P\[Severity-only baseline\]  
 	O \--\> Q\[Deterministic context baseline\]  
 	O \--\> R\[RandomForestRegressor\]

 	P \--\> S\[Scenario rankings\]  
 	Q \--\> S  
 	R \--\> S

 	S \--\> T\[NDCG@3 / NDCG@5\]  
 	S \--\> U\[Spearman\]  
 	R \--\> V\[MAE / RMSE diagnostics\]

 	T \--\> W\[Paired scenario-level comparison\]  
 	U \--\> W

 	W \--\> X\[Wilcoxon \+ effect size \+ bootstrap CI\]  
 	X \--\> Y\[Main conclusions\]

 	R \--\> Z\[Contrastive / ablation / permutation analysis\]

### **Unit of analysis phải được phân biệt**

Có ba “unit” khác nhau:

Finding   	\= ML observation  
 Scenario  	\= ranking \+ statistical observation  
 Family    	\= train/test grouping boundary

Đây là một trong những điểm quan trọng nhất của methodology. V2.3 đã quy định inferential analysis phải được thực hiện ở **scenario level**, không xem từng finding cùng scenario như các statistical observations độc lập. fileciteturn0file0

Ví dụ:

Family F07  
 ├── Scenario F07-A  
 │   ├── Finding 1  
 │   ├── Finding 2  
 │   └── Finding 3  
 └── Scenario F07-B  
 	├── Finding 1  
 	├── Finding 2  
 	└── Finding 3

Trong ML:

6 rows

nhưng trong split:

1 group \= F07

và trong B1 statistics:

2 scenario-level metric observations

không phải:

6 independent observations

### **Không cần deployment AWS thật**

terraform validate xác nhận configuration có cú pháp hợp lệ và nhất quán nội bộ nhưng không kiểm tra remote APIs; HashiCorp cũng hướng dẫn dùng terraform init \-backend=false khi muốn chuẩn bị working directory cho validation mà không truy cập backend. [*\[3\]*](https://developer.hashicorp.com/terraform/cli/commands/validate?utm_source=chatgpt.com) Checkov có thể scan trực tiếp Terraform source và cũng hỗ trợ Terraform plan JSON; plan có thể cho scanner thêm dependency/context, nhưng cũng tạo thêm complexity và có thể chứa các giá trị runtime nhạy cảm. [*\[4\]*](https://github.com/bridgecrewio/checkov/blob/main/docs/7.Scan%20Examples/Terraform%20Plan%20Scanning.md?utm_source=chatgpt.com)

Do đó, đối với thesis này:

Main path:  
 terraform validate  
 → source-code Checkov scan

là đủ.

terraform plan chỉ nên dùng cho những artifact mà feature extraction thật sự cần resolved values, không biến nó thành bắt buộc cho toàn dataset.

## **Dataset, Ground Truth và Feature Engineering**

### **Chiến lược ba tầng**

Tôi đồng ý hoàn toàn với Amendment v2.3:

SOURCE CORPUS  
   	↓  
 RESEARCH CORPUS  
   	↓  
 PRIORITIZATION BENCHMARK

fileciteturn0file0

Mục đích ba tầng:

| Tầng | Mục đích | Human annotation |
| :---- | :---- | ----: |
| Source Corpus | Candidate universe | Không |
| Research Corpus | RQ1 \+ screening | Không |
| Prioritization Benchmark | RQ2/RQ3 | Có |

Điểm này giúp một sinh viên không phải annotate hàng nghìn findings.

### **Nguồn dataset ưu tiên**

Một nguồn đặc biệt phù hợp là **Security-First Evaluation of Text-to-Terraform**, công bố tháng 8/2026: nghiên cứu đánh giá AWS Terraform từ bảy model trên 17 scenarios, sử dụng Checkov/Trivy và cho biết artifacts được công khai. Điều này gần như khớp trực tiếp với source-corpus requirement của thesis. [*\[5\]*](https://arxiv.org/abs/2608.02672?utm_source=chatgpt.com)

**GenIaC-SecBench** cũng đáng screening: bài báo mô tả 100 deployment scenarios, 1,196 IaC artifacts từ 12 model configurations và scan bằng Checkov, Trivy, KICS, đồng thời tuyên bố code/data/regeneration scripts được phát hành. Tuy nhiên, đây là công trình rất mới vào tháng 8/2026; bạn nên ghi rõ phiên bản dataset/commit được sử dụng và kiểm tra license trước khi ingest. [*\[6\]*](https://arxiv.org/abs/2608.28021?utm_source=chatgpt.com)

**IaC-Eval v2** có 186 AWS/Terraform tasks và là nguồn tốt cho task/resource diversity, nhưng bản thân dataset này là benchmark task/verification corpus, không nhất thiết là một kho GenAI-generated outputs phù hợp trực tiếp với research question của bạn. Vì vậy nên coi nó là **secondary source material**, không tự động coi mọi IaC-Eval artifact là “AI-generated Terraform”. [*\[7\]*](https://huggingface.co/datasets/iac-eval-v2/iac-eval-v2?utm_source=chatgpt.com)

Một benchmark có tên **IaCSecBench** hiện cũng tồn tại, nhưng repository được mô tả là framework/benchmark để đánh giá IaC security gates; nó không mặc định là GenAI-generated Terraform corpus. Vì vậy, với research story hiện tại, nó phù hợp hơn làm nguồn tham khảo về security-gate methodology hoặc external examples hơn là source chính cho claim “GenAI-generated Terraform”. [*\[8\]*](https://github.com/mchittineni/iacsecbench?utm_source=chatgpt.com)

### **Inclusion criteria**

Một artifact được đưa từ Source Corpus vào Research Corpus khi:

AWS Terraform  
 AND  
 provenance known  
 AND  
 license / usage acceptable  
 AND  
 terraform validate PASS  
 AND  
 Checkov scan succeeds  
 AND  
 \>= 1 in-scope finding

Đây là đúng policy v2.3. fileciteturn0file0

Với Prioritization Benchmark, thêm ưu tiên:

\>= 3 findings    → useful for NDCG@3  
 \>= 5 findings    → preferred for NDCG@5  
 category diversity  
 resource diversity  
 source diversity  
 family diversity  
 context relevance

Không được chọn scenario vì model xử lý nó tốt. fileciteturn0file0

### **Quy mô benchmark**

Giữ ba mức:

| Mức | Families | Context scenarios | Findings | Ý nghĩa |
| :---- | ----: | ----: | ----: | :---- |
| Preferred v2.3 | 40–60 | 80–120 | ≥300 preferred | Mục tiêu tốt |
| Practical target | 30–45 | 60–90 | khoảng 200–400 | Khả thi hơn cho một người |
| Contingency | 25–30 | 50–60 | tùy density | Chỉ dùng nếu annotation/time buộc phải giảm |

40–60 / 80–120 / ≥300 là planning target của chính v2.3, không phải hard minimum. fileciteturn0file0 Các mức Practical/Contingency ở trên là khuyến nghị quản trị tiến độ, không phải tuyên bố về statistical power.

Một KPI quan trọng hơn raw count là:

số scenario NDCG@3-eligible  
 số scenario NDCG@5-eligible  
 số family độc lập  
 category coverage  
 resource diversity

### **family\_id**

family\_id phải đại diện cho **cùng một base Terraform artifact hoặc cùng lineage đủ gần để có nguy cơ leakage**.

Ví dụ:

security-first\_s03\_gpt54\_run2  
 ├── Context A  
 └── Context B

cùng một family\_id.

Nếu có:

original artifact  
 → formatting-only copy  
 → context metadata variant  
 → small mechanically modified copy

tất cả nên cùng một family.

Nên lưu:

source\_id  
 source\_artifact\_id  
 family\_id  
 scenario\_id  
 content\_hash  
 resource\_signature

content\_hash hỗ trợ exact dedup; resource\_signature hỗ trợ phát hiện các artifacts gần như cùng một topology.

### **Annotation protocol**

Single annotator được **cho phép trong v2.3**, miễn là ghi rõ limitation; có thể self-retest một subset nhưng không được gọi self-retest là inter-annotator agreement. fileciteturn0file0

Một annotation record tối thiểu nên có:

scenario\_id  
 finding\_id  
 human\_rank  
 rationale  
 confidence  
 tie\_group\_optional  
 annotator\_id  
 annotation\_timestamp

Annotator được phép xem:

Terraform  
 check\_name  
 resource  
 objective features  
 scenario context

nhưng không được xem:

severity baseline output  
 context baseline score  
 RF prediction  
 model feature importance  
 NDCG  
 experiment results

Đây là đúng blind-annotation boundary của v2.3. fileciteturn0file0

### **Rubric nên như thế nào?**

Không nên biến rubric thành:

public \+3  
 prod \+3  
 sensitive \+3  
 IAM \+3

vì như vậy ground truth trở thành một deterministic formula, rồi Random Forest lại nhận chính các feature đó.

Thay vào đó, annotation guide nên đặt câu hỏi có cấu trúc:

| Dimension | Câu hỏi cho annotator |
| :---- | :---- |
| Exposure | Finding có tạo access từ untrusted network / Internet không? |
| Reachability | Resource thực sự có đường tiếp cận theo evidence hiện có không? |
| Privilege | Finding có cho phép mở rộng hoặc kiểm soát quyền đáng kể không? |
| Asset importance | Asset có quan trọng trong context được cung cấp không? |
| Data consequence | Dữ liệu có độ nhạy đáng kể không? |
| Environment | Prod/staging/dev ảnh hưởng urgency thế nào? |
| Compensating context | Có control/evidence nào làm giảm hoặc tăng urgency không? |

Việc dùng environmental/context reasoning có cơ sở khái niệm tốt: CVSS v4 tách Environmental metrics để phản ánh tính quan trọng của asset, security requirements và các đặc điểm riêng của deployment environment. Tuy nhiên CVSS không nên được sử dụng làm ground truth trực tiếp cho IaC finding prioritization. [*\[2\]*](https://www.first.org/cvss/v4.0/specification-document?utm_source=chatgpt.com)

Cuối mỗi finding annotator viết một rationale ngắn, ví dụ:

“Ưu tiên trên missing logging vì resource có direct Internet exposure trong production và rule ảnh hưởng đến access-control boundary.”

Rationale không dùng để train model; nó dùng để audit ground truth.

### **Xử lý ties**

Protocol v2.3 yêu cầu **unique Rank 1..N**. fileciteturn0file0 Vì vậy final ground truth không nên có ties.

Nhưng interface annotation có thể cho phép **provisional tie**:

F1 ≈ F2

sau đó dùng tie-break procedure:

1\. Compare direct exposure/reachability  
 2\. Compare privilege/data consequence  
 3\. Compare asset/business context  
 4\. Re-read Terraform evidence  
 5\. If still uncertain → expert/supervisor review if available  
 6\. Assign unique rank \+ mark low-confidence/tie\_group

Không được dùng model prediction để phá tie.

Trong trường hợp phải single-annotate và thật sự không phân biệt được F1/F2, giữ metadata:

tie\_group \= T01  
 confidence \= low

nhưng vẫn assign unique rank cho final protocol. Sau đó có thể chạy **ranking-sensitivity analysis** đổi thứ tự các finding trong tie group để xem conclusion có thay đổi không. Đây là cách minh bạch hơn việc giả vờ rằng human ordering là tuyệt đối chắc chắn.

### **Relevance mapping**

Giữ nguyên v2.3:

| Human rank | NDCG relevance |
| ----: | ----: |
| 1 | 3 |
| 2 | 2 |
| 3 | 1 |
| 4+ | 0 |

fileciteturn0file0

Scikit-learn định nghĩa NDCG bằng DCG của ranking được model sinh ra chia cho ideal DCG; score cao khi các item có true relevance cao được đẩy lên đầu ranking. [*\[9\]*](https://scikit-learn.org/dev/modules/generated/sklearn.metrics.ndcg_score.html?utm_source=chatgpt.com)

### **Optional second annotator**

A2 không nên trở thành dependency.

Nếu tìm được GVHD/security practitioner:

10–20% benchmark

là đủ hữu ích cho independent review.

A1 và A2 annotate blind, sau đó có thể tính Spearman agreement trên full rank và phân tích disagreements. Không cần bắt buộc A2 annotate toàn bộ dataset.

### **Feature schema đề xuất**

Main feature set:

| Feature | Loại | Nguồn | Main model |
| :---- | :---- | :---- | ----: |
| severity\_numeric | ordinal | frozen mapping | ✓ |
| scope\_category | categorical | frozen taxonomy | ✓ |
| resource\_type | categorical | Checkov/Terraform | ✓ |
| internet\_exposure | binary | Terraform evidence | ✓ |
| reachability | binary/unknown | Terraform evidence | ✓ |
| privilege\_impact | ordinal 0–3 | Terraform/IAM evidence | ✓ |
| environment | categorical/ordinal | metadata | ✓ |
| asset\_criticality | ordinal | metadata | ✓ |
| data\_sensitivity | ordinal | metadata | ✓ |
| public\_access | binary/NA | Terraform evidence | Optional |
| wildcard\_action | binary/NA | Terraform policy | Optional |
| wildcard\_resource | binary/NA | Terraform policy | Optional |
| encryption\_missing | binary/NA | Terraform/Checkov | Optional |
| logging\_missing | binary/NA | Terraform/Checkov | Optional |
| check\_id | categorical | Checkov | **Exclude main** |

Core internet\_exposure, privilege\_impact, reachability là bắt buộc theo v2.3. fileciteturn0file0

### **Feature extraction rules**

Mỗi feature cần một specification file, ví dụ:

internet\_exposure:  
   values:  
 	0: no direct internet exposure found  
 	1: direct internet exposure supported by Terraform evidence  
     null: cannot determine  
   evidence:  
 	\- cidr 0.0.0.0/0  
 	\- public access configuration  
 	\- public subnet / listener relation where determinable

privilege\_impact:

0 \= no privilege implication  
 1 \= broad/indirect permission implication  
 2 \= privilege expansion / permission management  
 3 \= unrestricted administrative/IAM control

đúng với đề xuất v2.3. fileciteturn0file0

**Không suy luận business context từ resource name.**

"payments-db"  
 ≠ automatically critical

Business context phải đến từ explicit metadata. fileciteturn0file2

### **Encoding**

Ordinal variables:

severity:  
 LOW=0  
 MEDIUM=1  
 HIGH=2  
 CRITICAL=3

và:

criticality:  
 low=0  
 medium=1  
 high=2

nếu taxonomy chỉ có ba mức.

Nominal variables như:

resource\_type  
 scope\_category  
 environment

có thể dùng OneHotEncoder(handle\_unknown="ignore"). Scikit-learn cung cấp OneHotEncoder cho categorical variables và ColumnTransformer để áp dụng transformer khác nhau cho từng loại cột. [*\[10\]*](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.OneHotEncoder?utm_source=chatgpt.com)

Riêng environment, bạn có hai lựa chọn:

One-hot:  
 dev/staging/prod

hoặc ordinal:

dev=0, staging=1, prod=2

Tôi khuyến nghị **one-hot** trong main model để không mặc định khoảng cách dev→staging bằng staging→prod.

### **Missing values**

Không được:

unknown → 0

nếu 0 có nghĩa “không có risk factor”.

Nên lưu:

unknown \= NA

và xử lý trong pipeline.

Một giải pháp đơn giản:

numeric/ordinal:  
 SimpleImputer(strategy="median", add\_indicator=True)

 categorical:  
 SimpleImputer(strategy="most\_frequent")  
 → OneHotEncoder(handle\_unknown="ignore")

Scikit-learn SimpleImputer hỗ trợ các chiến lược như mean/median/most-frequent/constant và có thể thêm missing indicator. [*\[11\]*](https://scikit-learn.org/1.8/modules/generated/sklearn.impute.SimpleImputer.html?utm_source=chatgpt.com)

Quan trọng:

**Imputer và encoder phải fit chỉ trên training fold.**

Không preprocess toàn dataset rồi mới cross-validation.

## **Baselines và thiết kế Machine Learning**

### **Severity-only baseline**

Pilot của dự án cho thấy Checkov output có thể trả severity=None, và v2.3 đã yêu cầu một severity mapping/policy độc lập phải được freeze trước evaluation. fileciteturn0file1 Checkov hỗ trợ severity-based CLI filtering trong một số configuration/API contexts, nhưng không nên giả định every offline finding JSON luôn có một usable severity. [*\[12\]*](https://github.com/bridgecrewio/checkov?utm_source=chatgpt.com)

Policy ưu tiên nên là:

Priority 1  
 Use scanner-provided severity if available and reproducible.

 Priority 2  
 Use a frozen check\_id → severity mapping  
 from authoritative Checkov/Prisma policy metadata where available.

 Priority 3  
 If unavailable, use a study-defined category severity proxy,  
 but call it "study severity mapping", not "Checkov severity".

Mapping artifact:

docs/severity\_mapping.csv

 check\_id  
 severity\_class  
 severity\_numeric  
 mapping\_source  
 source\_version  
 rationale

Freeze trước main annotation/model comparison.

Suggested numeric mapping:

LOW      \= 1  
 MEDIUM   \= 2  
 HIGH     \= 3  
 CRITICAL \= 4

Absolute numbers không quan trọng bằng ordering.

### **Tie handling cho severity baseline**

Severity-only gần như chắc chắn tạo ties.

Ví dụ:

F1 HIGH  
 F2 HIGH  
 F3 HIGH

Không được phá tie dựa trên human rank hoặc context.

Khi tính NDCG bằng scikit-learn, để:

ignore\_ties=False

để metric xử lý equal predicted scores thay vì giả định không có ties; đây cũng là default của ndcg\_score. [*\[9\]*](https://scikit-learn.org/dev/modules/generated/sklearn.metrics.ndcg_score.html?utm_source=chatgpt.com)

Nếu cần display ranking trong bảng, dùng deterministic neutral tie-break:

finding\_id ascending

nhưng metric phải dùng raw equal severity scores.

### **Deterministic contextual baseline**

Đây là baseline cực kỳ quan trọng.

Không nên xây công thức quá thông minh, vì mục tiêu là:

“Một contextual rule đơn giản đã đủ chưa?”

Một vấn đề lớn là scenario context giống nhau cho tất cả findings trong cùng scenario. Do đó công thức:

severity \+ environment \+ criticality \+ sensitivity

sẽ **không thay đổi relative ranking** nếu environment/criticality/sensitivity chỉ được cộng cùng một hằng số vào mọi finding.

Vì vậy context baseline phải có **interaction giữa finding-level fact và scenario context**.

Tôi khuyến nghị freeze một công thức đơn giản, minh bạch.

Đầu tiên normalize:

từ severity.

trong đó:

I \= internet\_exposure ∈ \[0,1\]  
 R \= reachability ∈ \[0,1\]  
 P \= privilege\_impact / 3

Business context:

với:

E \= environment risk  
 A \= asset criticality  
 D \= data sensitivity

được normalize về \[0,1\].

Sau đó:

Ý nghĩa:

45% intrinsic / scanner severity  
 30% finding-specific technical context  
 25% interaction giữa technical risk và business context

Tổng trọng số bằng 1\.

Điểm quan trọng ở đây là C **không được cộng độc lập**, mà xuất hiện qua T × C. Vì vậy production/high-sensitivity chỉ tăng score khi finding có technical pathway liên quan.

Đây không phải “công thức risk đúng nhất”. Nó là **transparent deterministic baseline**. Trọng số phải được freeze trước final experiment và không được chỉnh vì Random Forest thắng hoặc thua.

Nên thực hiện một robustness check nhỏ:

Main:  
 0.45 / 0.30 / 0.25

 Sensitivity:  
 0.50 / 0.25 / 0.25  
 0.40 / 0.30 / 0.30

nhưng không chọn công thức tốt nhất sau khi xem test result. Chỉ báo cáo xem conclusion có nhạy với reasonable weight variation hay không.

### **So sánh các phương pháp**

| Khía cạnh | Severity-only | Context Rule | Random Forest |
| :---- | ----: | ----: | ----: |
| Scanner severity | ✓ | ✓ | ✓ |
| Technical context | ✗ | ✓ | ✓ |
| Business context | ✗ | ✓ | ✓ |
| Học từ data | ✗ | ✗ | ✓ |
| Explainability | Rất cao | Rất cao | Trung bình |
| Overfitting risk | Thấp | Thấp | Có |
| Circularity risk | Thấp | Cao vừa | Cao |
| Implementation | Rất thấp | Thấp | Trung bình |
| MUST | ✓ | ✓ | ✓ |

### **RandomForestRegressor**

Random Forest là lựa chọn phù hợp cho thesis này vì scikit-learn định nghĩa nó là ensemble của nhiều regression trees được fit trên các subsamples và average predictions; nó hoạt động tốt với tabular features và không cần neural-network stack. [*\[13\]*](https://scikit-learn.org/dev/modules/generated/sklearn.ensemble.RandomForestRegressor.html?utm_source=chatgpt.com)

Main pipeline:

Raw Feature DataFrame  
         ↓  
 ColumnTransformer  
         ↓  
 Imputation  
         ↓  
 One-Hot Encoding  
         ↓  
 RandomForestRegressor  
         ↓  
 Continuous Priority Score

Không cần feature scaling cho tree model.

### **Target tôi khuyến nghị**

Từ unique human rank:

Ví dụ:

| Rank trong scenario 5 findings | y |
| ----: | ----: |
| 1 | 1.00 |
| 2 | 0.75 |
| 3 | 0.50 |
| 4 | 0.25 |
| 5 | 0.00 |

Đây là target cho regression.

Riêng NDCG vẫn dùng:

3, 2, 1, 0, 0...

Việc tách:

training target  
 ≠  
 NDCG relevance

là hoàn toàn hợp lý vì một cái phục vụ học pointwise ordering, một cái định nghĩa top-k utility.

### **Hyperparameters**

Do bạn chưa học ML, tôi **không khuyến nghị GridSearch cực lớn**.

Vì bạn đã có Pilot riêng, cách khoa học và đơn giản hơn là:

Chọn hyperparameters từ pilot, freeze chúng trước main evaluation.

Một starting configuration hợp lý:

RandomForestRegressor(  
     n\_estimators=500,  
     max\_depth=None,  
     min\_samples\_split=2,  
     min\_samples\_leaf=2,  
     max\_features="sqrt",  
     bootstrap=True,  
     random\_state=42,  
 	n\_jobs=-1  
 )

Scikit-learn hỗ trợ trực tiếp các parameter này và random\_state dùng để kiểm soát randomness/reproducibility. [*\[13\]*](https://scikit-learn.org/dev/modules/generated/sklearn.ensemble.RandomForestRegressor.html?utm_source=chatgpt.com)

Nếu pilot cho thấy cần tuning, giới hạn ở một search nhỏ:

| Hyperparameter | Values |
| :---- | :---- |
| n\_estimators | 300, 500 |
| max\_depth | None, 8, 16 |
| min\_samples\_leaf | 1, 2, 4 |
| max\_features | "sqrt", 0.5, 1.0 |

Không cần tuning 20+ parameters.

Quan trọng hơn: **không tune trên final test folds**.

### **Primary split**

Tôi đề xuất:

**Five-fold GroupKFold by family\_id là primary evaluation strategy.**

Scikit-learn GroupKFold đảm bảo cùng một group không xuất hiện đồng thời ở hai folds; mỗi group xuất hiện một lần trong test across folds. [*\[14\]*](https://scikit-learn.org/dev/modules/generated/sklearn.model_selection.GroupKFold.html?utm_source=chatgpt.com)

Với khoảng 40–60 families:

Fold 1 test ≈ 8–12 families  
 ...  
 Fold 5 test ≈ 8–12 families

đủ hợp lý.

Pipeline:

for fold:  
 	TRAIN families  
     	↓  
 	fit preprocessing  
     	↓  
 	fit RF  
     	↓  
 	TEST unseen families  
     	↓  
 	save out-of-fold scores

Sau năm folds:

mọi scenario đều có out-of-fold prediction

và tất cả main metrics được tính từ prediction không được train trực tiếp trên family đó.

### **Leave-One-Family-Out**

LOFO nên dùng như **robustness check**, không phải primary strategy.

Nếu 45 families:

45 train/evaluate iterations

vẫn computationally nhẹ cho Random Forest, nhưng result có thể biến động mạnh theo từng family. GroupKFold dễ trình bày và dễ thống kê hơn.

Nếu benchmark cuối chỉ có rất ít families, LOFO có thể trở thành primary fallback.

### **check\_id policy**

Main experiment:

check\_id \= EXCLUDED

Reason:

check\_id → finding identity  
     	→ shortcut to typical rank

Protocol v2.3 đã cảnh báo trực tiếp về nguy cơ này. fileciteturn0file0

Supplementary sensitivity:

RF-main:  
 without check\_id

 RF-id:  
 with check\_id

Nếu:

RF-id \>\> RF-main

thì đây là một finding quan trọng:

model performance phụ thuộc mạnh vào policy identity.

Không nhất thiết là improvement tích cực.

### **Các leakage checkpoint bắt buộc**

Feature extraction  
     BEFORE annotation

 Family construction  
     BEFORE split

 Split  
     BEFORE preprocessing fit

 Imputer/encoder fit  
     ONLY on training fold

 Hyperparameters  
     frozen from pilot / training only

 Test predictions  
     never shown to annotator

 Ground truth  
     never revised after model results

Đây chính là logic data-leakage prevention của protocol. fileciteturn0file0

## **Evaluation, thống kê và các thí nghiệm bổ sung**

### **Primary metrics**

Giữ nguyên:

NDCG@3  
 NDCG@5

NDCG được thiết kế để thưởng cho việc đưa item relevance cao lên vị trí đầu và normalize bằng ideal DCG thành score thường nằm trong \[0,1\] khi relevance không âm. [*\[9\]*](https://scikit-learn.org/dev/modules/generated/sklearn.metrics.ndcg_score.html?utm_source=chatgpt.com)

Eligibility:

NDCG@3 → scenario có \>=3 findings  
 NDCG@5 → scenario có \>=5 findings

theo Blueprint/Protocol của bạn. fileciteturn0file0 fileciteturn0file2

Tuyệt đối không báo:

NDCG@5 over all scenarios

nếu nhiều scenario chỉ có 2–3 findings mà không nói rõ eligibility policy.

### **Secondary metric**

Spearman correlation:

human rank  
 vs  
 predicted score/rank

Spearman đo mức độ monotonic association giữa hai ranking/variables và nằm trong khoảng \[-1,+1\]. [*\[15\]*](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.spearmanr.html?utm_source=chatgpt.com)

Lưu ý: nếu một baseline tạo constant scores trong scenario, Spearman có thể không xác định. SciPy phát ConstantInputWarning và trả NaN cho constant input. [*\[15\]*](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.spearmanr.html?utm_source=chatgpt.com)

Vì vậy:

Do not:  
 NaN → 0 silently

Hãy báo:

eligible scenarios  
 valid Spearman scenarios  
 NaN/constant-score count  
 median Spearman  
 IQR

### **Diagnostic metrics**

MAE và RMSE dùng cho regression target:

normalized\_priority

Nhưng chúng là diagnostic metrics.

Main research conclusion phải ưu tiên:

NDCG

vì thesis quan tâm thứ tự remediation hơn absolute numeric score.

### **Scenario-level aggregation**

Mỗi fold sinh finding predictions.

Sau đó:

Findings  
    ↓  
 group by scenario\_id  
    ↓  
 sort predicted score  
    ↓  
 calculate NDCG/Spearman

Final result table:

| Scenario | Method | NDCG@3 | NDCG@5 | Spearman |
| :---- | :---- | ----: | ----: | ----: |
| S01 | Severity | ... | ... | ... |
| S01 | Context | ... | ... | ... |
| S01 | RF | ... | ... | ... |
| S02 | Severity | ... | ... | ... |

Statistical analysis sử dụng các row scenario-level này, không raw findings. fileciteturn0file0

### **Main statistical comparisons**

Chỉ cần hai formal comparisons:

C1:  
 Context Rule vs Severity

 C2:  
 Random Forest vs Context Rule

XGBoost không có thì không sao.

Primary test:

Wilcoxon signed-rank

vì metric được paired theo cùng scenario. SciPy mô tả Wilcoxon signed-rank là kiểm định phi tham số cho hai related paired samples và kiểm tra distribution của pairwise differences quanh zero. [*\[16\]*](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.wilcoxon.html)

Tôi khuyên:

alternative="two-sided"

trong main analysis.

Sau đó direction được báo qua:

median difference  
 effect size  
 confidence interval

Thay vì preregister one-sided “ML must be greater”.

### **Zero differences và ties trong Wilcoxon**

Security/context baselines có thể tạo nhiều metric bằng nhau:

ΔNDCG \= 0

SciPy cung cấp nhiều zero-handling conventions (wilcox, pratt, zsplit) và cảnh báo ties/zeros ảnh hưởng exact null distribution; với ties/zeros, permutation-based computation có thể phù hợp hơn trong một số trường hợp. [*\[16\]*](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.wilcoxon.html)

Tôi đề xuất freeze:

primary:  
 zero\_method="wilcox"  
 alternative="two-sided"  
 method="auto"

và robustness:

zero\_method="pratt"

Nếu conclusion đổi chỉ vì zero-handling method thì phải báo limitation.

### **Effect size**

Nên báo một **matched-pairs rank-biserial effect size** cùng Wilcoxon.

Có thể tính:

trong đó:

W+ \= tổng rank của positive differences  
 W- \= tổng rank của negative differences

Interpretation:

positive → method A tends higher  
 negative → method B tends higher  
 near 0 → little directional dominance

Không cần biến effect-size category "small/medium/large" thành rigid truth; raw value \+ CI hữu ích hơn.

### **Bootstrap confidence interval**

Báo 95% bootstrap CI cho:

median ΔNDCG

hoặc:

mean ΔNDCG

nhưng tôi khuyên median vì NDCG differences có thể skewed.

SciPy bootstrap hỗ trợ paired resampling và BCa confidence intervals. [*\[17\]*](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html?utm_source=chatgpt.com)

Với main B1:

bootstrap unit \= scenario

Với B2 contrastive:

bootstrap unit \= family

không resample từng matched finding độc lập.

### **Output thống kê nên trông như thế nào?**

Ví dụ cấu trúc:

| Comparison | n scenarios | Median A | Median B | Median Δ | 95% CI Δ | Effect | p |
| :---- | ----: | ----: | ----: | ----: | :---- | ----: | ----: |
| Context vs Severity | 31 | ... | ... | ... | \[...\] | ... | ... |
| RF vs Context | 31 | ... | ... | ... | \[...\] | ... | ... |

Không chỉ báo:

p \= 0.032

### **Contrastive A/B experiment**

B2 giữ nguyên như v2.3:

same / equivalent Terraform  
           │  
      ┌────┴────┐  
      ▼     	▼  
 Context A   Context B  
 low risk    high risk  
      │     	│  
      ▼     	▼  
 score\_A     score\_B

Matched finding:

same check\_id  
 \+  
 same normalized logical resource address

fileciteturn0file0

Metric:

Descriptive:

Nhưng **inferential unit phải là family**.

Ví dụ:

Family F1:  
 median Δ across matched findings \= 0.14

 Family F2:  
 median Δ \= 0.02

rồi statistical analysis trên family summaries. fileciteturn0file0

### **Đừng hiểu sai B2**

B2 không hỏi:

“Ranking scenario B có tốt hơn A không?”

Mà hỏi:

“Cùng một finding, model score có phản ứng khi contextual risk tăng không?”

Đây là hai construct khác nhau.

### **Ablation**

Chỉ cần ablation tối thiểu:

RF-All  
 vs  
 RF-NoBusinessContext

Trong đó:

NoBusinessContext removes:  
 environment  
 asset\_criticality  
 data\_sensitivity

Nếu còn thời gian:

RF-NoExposure  
 RF-NoPrivilege  
 RF-NoReachability

Nhưng đừng chạy 20 tổ hợp.

Một ablation đặc biệt quan trọng:

RF-NoBusinessContext

vì nó trực tiếp kiểm tra thesis construct.

### **Feature importance**

Random Forest impurity-based importance có thể được báo như exploratory output, nhưng không nên xem nó là bằng chứng causal.

Permutation importance tốt hơn như một secondary interpretation vì nó đo mức giảm model score khi một feature được shuffle; scikit-learn cũng nhấn mạnh permutation importance phản ánh feature quan trọng **đối với model cụ thể trên dataset cụ thể**, không phải intrinsic predictive value tuyệt đối của feature. [*\[18\]*](https://scikit-learn.org/1.0/modules/permutation_importance.html?utm_source=chatgpt.com)

Do thesis metric chính là ranking, lý tưởng nhất permutation function nên đo:

scenario-level NDCG

nhưng implementation này phức tạp hơn.

Với người mới ML, có thể:

Permutation importance on normalized-priority MAE/R2  
 \+  
 NDCG ablation for key feature groups

và nói rõ limitation.

### **Robustness checks nên giữ ít**

Bộ robustness vừa đủ:

| Check | Mục tiêu |
| :---- | :---- |
| GroupKFold vs LOFO | Split sensitivity |
| Context baseline reasonable weight variants | Baseline weight sensitivity |
| RF with/without check\_id | Shortcut sensitivity |
| RF with/without business context | Context contribution |
| Single annotation vs re-test subset | Annotation stability |

Không cần thêm model thứ tư/thứ năm.

## **Reproducibility, tiêu chí thành công và các bẫy cần tránh**

### **Version pinning**

Protocol đã chọn Checkov 3.3.17; PyPI xác nhận 3.3.17 được phát hành ngày 10/09/2026 và package có publish provenance/checksum. [*\[19\]*](https://pypi.org/project/checkov/3.3.17/?utm_source=chatgpt.com) Vì experiment của bạn bắt đầu sau ngày đó, đây là version hoàn toàn hợp lý để freeze.

Pin ít nhất:

Terraform exact version  
 AWS provider constraint / lockfile  
 Checkov \== 3.3.17  
 Python exact minor version  
 pandas  
 numpy  
 scikit-learn  
 scipy  
 joblib

terraform init tạo .terraform.lock.hcl, và HashiCorp giải thích lock file giúp giữ provider versions nhất quán giữa các execution environments. [*\[20\]*](https://developer.hashicorp.com/terraform/tutorials/cli/init?utm_source=chatgpt.com)

### **Artifact cần lưu**

source\_inventory.csv  
 research\_corpus\_inventory.csv  
 prioritization\_benchmark.csv

 terraform/  
 raw\_checkov/  
 normalized\_findings/  
 context\_metadata/  
 features/  
 annotations/

 severity\_mapping.csv  
 context\_baseline\_config.yaml

 splits/  
 predictions/  
 metrics/  
 statistics/

 models/  
 logs/  
 environment/  
 figures/

Với mỗi experiment:

{  
   "experiment\_id": "...",  
   "git\_commit": "...",  
   "dataset\_version": "...",  
   "feature\_schema\_version": "...",  
   "annotation\_version": "...",  
   "checkov\_version": "3.3.17",  
   "random\_seed": 42,  
   "split\_strategy": "GroupKFold",  
   "n\_splits": 5,  
   "model\_params": {}  
 }

### **Random seeds**

Freeze:

42

hoặc bất kỳ integer nào, nhưng đừng thay seed để chọn kết quả đẹp. Scikit-learn nêu rõ fixed integer random\_state giúp tạo deterministic behavior cho randomization của estimator/splitter tương ứng. [*\[21\]*](https://scikit-learn.org/dev/modules/generated/sklearn.ensemble.RandomForestRegressor.html?utm_source=chatgpt.com)

Một robustness check có thể chạy:

seed \= 1, 7, 42, 123, 2026

sau khi main result đã freeze, nhằm xem RF conclusion có phụ thuộc mạnh vào seed không.

### **Success criteria**

Research **PASS** nếu:

✓ Research corpus có provenance  
 ✓ Benchmark được freeze trước model results  
 ✓ Feature extraction reproducible  
 ✓ Human ranks \+ rationale hoàn chỉnh  
 ✓ No family leakage  
 ✓ Severity baseline chạy  
 ✓ Context baseline chạy  
 ✓ RF tạo out-of-fold predictions  
 ✓ NDCG@3/@5 được tính theo eligibility policy  
 ✓ Main paired comparison hoàn thành  
 ✓ Limitations được báo cáo  
 ✓ Full rerun tái tạo được result

Không yêu cầu:

RF \> Context

### **Interpretation matrix**

| Kết quả | Kết luận hợp lệ |
| :---- | :---- |
| Context \> Severity; RF \> Context | Context hữu ích; ML có thêm signal |
| Context \> Severity; RF ≈ Context | Context hữu ích; chưa chứng minh cần ML |
| Context \> Severity; RF \< Context | Context hữu ích; deterministic rule tốt hơn RF trên benchmark |
| Severity ≈ Context ≈ RF | Benchmark chưa cho thấy context/ML cải thiện |
| RF tốt nhưng ablation cho thấy phụ thuộc check\_id | Có shortcut concern, không claim context learning mạnh |

Negative-result policy này phù hợp hoàn toàn với v2.3. fileciteturn0file0

### **Kill-switch decisions**

Do bạn chỉ có khoảng mười tuần effective time, kill-switch cần được quyết định trước:

| Trigger | Quyết định |
| :---- | :---- |
| Research corpus nhỏ hơn dự kiến | Giảm benchmark target, không tự sinh hàng nghìn samples |
| Annotation chậm \> dự kiến | Giảm family count, giữ finding density |
| Ít scenario ≥5 findings | Ưu tiên benchmark selection cho NDCG@5 coverage |
| A2 không tìm được | Proceed single annotator \+ self-retest \+ limitation |
| RF pipeline chạy ổn | Không thêm model khác |
| XGBoost chưa bắt đầu đến cuối tuần 7 | Bỏ |
| GitHub Actions chưa làm đến cuối tuần 8 | CLI/JSON đủ |
| Feature importance phức tạp | Chỉ RF importance \+ one ablation |
| Main pipeline lỗi | Gate bị hoãn, research experiment ưu tiên |
| RF không hơn rule | Chấp nhận negative result |
| Ground truth không đáng tin | Giảm strength of claims; không cố train thêm model |

### **Bẫy lớn nhất: ground-truth circularity**

Ví dụ xấu:

Rubric:  
 Production \+3  
 Sensitive  \+3  
 Public 	\+3

 ↓ label

 ML inputs:  
 production  
 sensitive  
 public

 ↓ model

 NDCG \= 0.95

Kết luận:

"ML discovers risk"

là quá mạnh.

Kết luận hợp lý hơn:

Model có khả năng tái tạo và generalize study-defined contextual prioritization trên unseen Terraform families.

Blueprint v2.1 đã nhận diện chính xác rằng nếu ground truth được tạo chủ yếu từ cùng features mà model nhận, model có thể đơn giản học lại rubric. fileciteturn0file2

Mitigation:

rationale-based annotation  
 not additive-label formula

 family-level split

 context rule baseline

 business-context ablation

 check\_id exclusion

 transparent construct validity discussion

### **Bẫy thứ hai: leakage**

Sai:

Context A → train  
 Context B → test

của cùng Terraform.

Đúng:

Family F03:  
 A \+ B → same fold

GroupKFold được thiết kế chính xác để giữ group không overlap giữa train và test. [*\[14\]*](https://scikit-learn.org/dev/modules/generated/sklearn.model_selection.GroupKFold.html?utm_source=chatgpt.com)

### **Bẫy thứ ba: “context baseline” không thật sự thay đổi ranking**

Công thức:

score \=  
 severity  
 \+ prod  
 \+ criticality  
 \+ sensitivity

nếu ba context cuối cùng giống cho mọi finding trong scenario thì:

Finding A HIGH → 8  
 Finding B MEDIUM → 7

 switch DEV → PROD:

 Finding A → 10  
 Finding B → 9

ranking vẫn y hệt.

Vì vậy deterministic baseline phải có **finding × context interaction**.

### **Bẫy thứ tư: dùng accuracy**

Đây không phải classification task.

Accuracy \= không phải main metric

Main output là ordering.

NDCG@K phù hợp trực tiếp hơn với top-of-ranking utility. [*\[9\]*](https://scikit-learn.org/dev/modules/generated/sklearn.metrics.ndcg_score.html?utm_source=chatgpt.com)

### **Bẫy thứ năm: feature importance \= causality**

Không được viết:

internet\_exposure có feature importance cao nên Internet exposure “gây ra” security risk.

Hợp lý hơn:

Trong model và benchmark này, perturbing hoặc removing internet\_exposure làm giảm predictive/ranking performance.

Permutation importance cũng được scikit-learn mô tả là model-specific, không phải intrinsic feature value. [*\[18\]*](https://scikit-learn.org/1.0/modules/permutation_importance.html?utm_source=chatgpt.com)

### **Bẫy thứ sáu: scanner finding \= vulnerability độc lập**

Protocol đã cảnh báo một Terraform root cause có thể sinh nhiều Checkov rules. fileciteturn0file0

Do đó viết:

“314 Checkov security findings”

không phải:

“314 independent vulnerabilities”.

## **Kế hoạch thực hiện mười tuần**

Mười tuần này nên được coi là **effective execution window**; phần buffer hai tuần sau đó không được dùng để mở thêm research scope.

| Tuần | Trọng tâm | Deliverable bắt buộc | Contingency / kill decision |
| :---- | :---- | :---- | :---- |
| **Tuần 1** | Freeze methodology \+ source acquisition | protocol\_frozen.md, source inventory, environment lock | Không tìm thêm nguồn nếu đã có ≥2 nguồn tốt |
| **Tuần 2** | Validate \+ Checkov \+ research corpus | Raw Terraform, validate logs, Checkov JSON, research corpus inventory | Loại artifact dependency quá phức tạp |
| **Tuần 3** | Benchmark selection \+ feature extraction | family\_id, benchmark candidates, frozen feature schema | Nếu density thấp, ưu tiên ≥5-findings families |
| **Tuần 4** | Context construction \+ annotation pilot | Context A/B, annotation guide, 10–20% annotated | Sửa rubric duy nhất ở đây, sau đó freeze |
| **Tuần 5** | Main annotation \+ QA | Frozen ground truth, rationale, self-retest subset | Nếu chậm, giảm families thay vì bỏ rationale |
| **Tuần 6** | Baselines | Severity mapping, severity predictions, context baseline | Freeze formula; không chỉnh theo RF |
| **Tuần 7** | Random Forest \+ group CV | OOF RF predictions, model configs, initial NDCG | Nếu RF chạy: dừng thêm model |
| **Tuần 8** | Main evaluation \+ B2 | NDCG@3/5, Spearman, contrastive output | XGBoost chưa có → bỏ |
| **Tuần 9** | Statistics \+ ablation \+ reproducibility | Wilcoxon, effect size, bootstrap CI, one ablation, full rerun | Gate chỉ CLI nếu thiếu thời gian |
| **Tuần 10** | Freeze \+ thesis package \+ prototype | Final tables/figures, CLI gate, methodology/results draft | **STOP FEATURE DEVELOPMENT** |

### **Tuần đầu**

Mục tiêu là không code ML.

Freeze:

RQ  
 inclusion criteria  
 family definition  
 feature schema  
 annotation rubric  
 severity mapping strategy  
 NDCG relevance mapping  
 primary split  
 RF target

Đồng thời thu Source Corpus.

Security-First Evaluation và GenIaC-SecBench là hai candidate sources có giá trị cao vì đều công bố GenAI IaC/security evaluation artifacts. [*\[22\]*](https://arxiv.org/abs/2608.02672?utm_source=chatgpt.com)

**Definition of Done:** bạn có thể trả lời bằng văn bản “một row trong dataset cuối là gì?”.

### **Tuần hai**

Chạy:

terraform init \-backend=false  
 terraform validate  
 Checkov 3.3.17

và lưu toàn bộ raw output.

HashiCorp yêu cầu initialized working directory cho validation khi provider/module liên quan cần được cài, còn Checkov hỗ trợ scanning Terraform trực tiếp và JSON output. [*\[23\]*](https://developer.hashicorp.com/terraform/cli/commands/validate?utm_source=chatgpt.com)

**Definition of Done:** Research Corpus có provenance \+ validation \+ raw Checkov findings.

### **Tuần ba**

Làm:

dedup  
 family\_id  
 scenario\_id  
 category mapping  
 finding normalization  
 technical feature extraction

Feature definitions phải freeze trước annotation. fileciteturn0file0

**Definition of Done:** mỗi finding có structured row mà chưa có human\_rank.

### **Tuần bốn**

Tạo Context A/B và chạy annotation pilot khoảng 10–20% benchmark.

Mục tiêu tuần này không phải hoàn tất annotation, mà phát hiện:

rubric không rõ  
 tie quá nhiều  
 rationale khó viết  
 finding evidence thiếu

Đây là **cơ hội cuối** sửa annotation guide trước freeze.

**Definition of Done:** annotation protocol ổn định.

### **Tuần năm**

Main annotation.

Không train RF trong lúc annotation đang làm để tránh temptation xem prediction rồi sửa label.

Cuối tuần:

ground\_truth\_v1.csv  
 annotation\_log.csv  
 rationale complete

Nếu single annotator, self-retest random khoảng 10% sau vài ngày và báo stability descriptively; không gọi đây là inter-annotator agreement. Điều này phù hợp v2.3. fileciteturn0file0

### **Tuần sáu**

Hoàn thành:

Severity baseline  
 Context baseline

Freeze:

severity\_mapping.yaml  
 context\_baseline.yaml

Không mở Random Forest result trước khi baseline đã frozen.

**Definition of Done:** hai baseline đều tạo predicted score/ranking cho toàn benchmark.

### **Tuần bảy**

Đây mới là tuần ML chính.

Học đủ:

X  
 y  
 fit  
 predict  
 cross-validation  
 overfitting  
 feature encoding  
 GroupKFold

Sau đó build Random Forest pipeline.

Random Forest của scikit-learn là ensemble regression estimator và GroupKFold cho phép các family groups không overlap giữa train/test. [*\[24\]*](https://scikit-learn.org/dev/modules/generated/sklearn.ensemble.RandomForestRegressor.html?utm_source=chatgpt.com)

**Definition of Done:** mọi scenario có out-of-fold RF scores.

### **Tuần tám**

Main evaluation:

Severity  
 vs  
 Context  
 vs  
 RF

tính:

NDCG@3  
 NDCG@5  
 Spearman

và B2:

Δscore  
 CDA  
 family median Δ

**Kill rule:** không thêm XGBoost nếu main results chưa clean.

### **Tuần chín**

Statistics:

Wilcoxon  
 rank-biserial effect  
 95% bootstrap CI

Ablation:

RF-All  
 vs  
 RF-NoBusinessContext

và check\_id sensitivity nếu kịp.

SciPy hỗ trợ paired Wilcoxon và paired bootstrap/resampling constructs cần thiết cho các phân tích này. [*\[25\]*](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.wilcoxon.html)

Sau đó full reproducibility run từ clean environment.

### **Tuần mười**

Không research mới.

Làm:

final figures  
 final tables  
 thesis methodology  
 results  
 discussion  
 threats to validity  
 CLI/JSON Security Gate  
 README  
 demo script

**Rule cuối tuần:**

**STOP FEATURE DEVELOPMENT.**

Nếu GitHub Actions chưa xong, không sao. Workflow v2.3 đã cho phép CLI/JSON đủ cho prototype; Security Gate là application layer, không phải scientific contribution chính. fileciteturn0file1

### **Hai tuần buffer sau kế hoạch**

Hai tuần dự phòng không được xem như Week 11–12 để thêm chức năng.

Chỉ sử dụng cho:

bug fixing  
 rerun khi artifact lỗi  
 thesis editing  
 citation cleanup  
 figures/tables correction  
 demo rehearsal  
 slides  
 defense Q\&A

Nếu mọi thứ hoàn thành sớm, mới cân nhắc:

GitHub Actions

hoặc:

XGBoost

chứ không thêm cả hai.

## **Methodology đề xuất để freeze**

Sau khi đối chiếu tài liệu dự án với primary documentation và các benchmark IaC hiện tại, tôi khuyến nghị bản methodology cuối cùng của bạn được freeze như sau:

RESEARCH CONTEXT  
 Generative-AI-generated AWS Terraform  
     	↓

 DATA  
 Reuse public/reproducible prior-work artifacts  
     	↓  
 Source Corpus  
     	↓  
 AWS \+ Terraform \+ valid \+ scanable \+ provenance  
     	↓  
 Research Corpus  
     	↓  
 Predefined stratified selection  
     	↓  
 Prioritization Benchmark  
     	↓

 SECURITY ANALYSIS  
 terraform validate  
 \+  
 Checkov 3.3.17  
     	↓  
 Normalized Security Findings  
     	↓

 CONTEXT  
 Finding-level:  
 \- internet\_exposure  
 \- privilege\_impact  
 \- reachability  
 \- selected objective facts

 Scenario-level:  
 \- environment  
 \- asset\_criticality  
 \- data\_sensitivity  
     	↓

 GROUND TRUTH  
 Blind human ranking  
 \+  
 mandatory rationale  
 \+  
 single annotator allowed  
 \+  
 optional independent subset review  
     	↓  
 Rank 1...N  
     	↓  
 Normalized priority target for RF  
 \+  
 NDCG relevance 3/2/1/0  
     	↓

 METHODS  
 Severity-only  
     	vs  
 Deterministic Context  
     	vs  
 RandomForestRegressor  
     	↓

 SPLIT  
 5-fold GroupKFold  
 groups \= family\_id  
     	↓

 PRIMARY EVALUATION  
 NDCG@3  
 NDCG@5  
     	↓

 SECONDARY  
 Spearman  
     	↓

 DIAGNOSTIC  
 MAE  
 RMSE  
     	↓

 STATISTICS  
 Scenario-level paired comparison  
 Wilcoxon  
 effect size  
 bootstrap 95% CI  
     	↓

 SECONDARY EXPERIMENT  
 Context A/B  
 matched finding Δscore  
 family-level inference  
     	↓

 EXPLORATORY  
 RF importance  
 permutation importance  
 business-context ablation  
 check\_id sensitivity  
     	↓

 PROTOTYPE  
 Terraform  
 → Checkov  
 → Context  
 → RF score  
 → Ranking  
 → CLI/JSON Security Gate

Đây là mức methodology đủ sâu cho một luận văn theo hướng nghiên cứu nhưng vẫn phù hợp với người **chưa từng học Machine Learning**.

Phần ML bạn thực sự phải học chỉ là:

feature  
 target  
 training  
 prediction  
 overfitting  
 cross-validation  
 Random Forest  
 NDCG

Phần khó hơn, và cũng là nơi chất lượng luận văn được quyết định, là:

Dataset validity  
 Ground truth validity  
 Leakage prevention  
 Fair baselines  
 Correct evaluation  
 Honest interpretation

Điểm mạnh của đề tài không nên được kể là:

“Em dùng Random Forest để áp dụng AI vào security.”

Mà nên được kể là:

**“Em thiết kế một controlled empirical study để kiểm tra liệu deployment context có cải thiện việc ưu tiên các Terraform security findings hay không, và liệu một mô hình Machine Learning đơn giản có tạo thêm giá trị so với deterministic context-aware scoring hay không.”**

Đó là framing vừa **đúng với Network & Security/DevSecOps**, vừa đáp ứng yêu cầu **AI**, vừa có cấu trúc **nghiên cứu khoa học**, mà không buộc một sinh viên chưa học ML phải biến luận văn thành một dự án AI quá nặng. fileciteturn0file0 fileciteturn0file1 fileciteturn0file2

---

[*\[1\]* *\[12\]*](https://github.com/bridgecrewio/checkov?utm_source=chatgpt.com) GitHub \- bridgecrewio/checkov: Prevent cloud misconfigurations and find vulnerabilities during build-time in infrastructure as code, container images and open source packages with Checkov by Bridgecrew. · GitHub

[*https://github.com/bridgecrewio/checkov?utm\_source=chatgpt.com*](https://github.com/bridgecrewio/checkov?utm_source=chatgpt.com)

[*\[2\]*](https://www.first.org/cvss/v4.0/specification-document?utm_source=chatgpt.com) CVSS v4.0 Specification Document

[*https://www.first.org/cvss/v4.0/specification-document?utm\_source=chatgpt.com*](https://www.first.org/cvss/v4.0/specification-document?utm_source=chatgpt.com)

[*\[3\]* *\[23\]*](https://developer.hashicorp.com/terraform/cli/commands/validate?utm_source=chatgpt.com) terraform validate command reference | Terraform | HashiCorp Developer

[*https://developer.hashicorp.com/terraform/cli/commands/validate?utm\_source=chatgpt.com*](https://developer.hashicorp.com/terraform/cli/commands/validate?utm_source=chatgpt.com)

[*\[4\]*](https://github.com/bridgecrewio/checkov/blob/main/docs/7.Scan%20Examples/Terraform%20Plan%20Scanning.md?utm_source=chatgpt.com) checkov/docs/7.Scan Examples/Terraform Plan Scanning.md at main · bridgecrewio/checkov · GitHub

[*https://github.com/bridgecrewio/checkov/blob/main/docs/7.Scan%20Examples/Terraform%20Plan%20Scanning.md?utm\_source=chatgpt.com*](https://github.com/bridgecrewio/checkov/blob/main/docs/7.Scan%20Examples/Terraform%20Plan%20Scanning.md?utm_source=chatgpt.com)

[*\[5\]* *\[22\]*](https://arxiv.org/abs/2608.02672?utm_source=chatgpt.com) Security-First Evaluation of Text-to-Terraform: Benchmarking LLMs and SLMs for Secure IaC Generation

[*https://arxiv.org/abs/2608.02672?utm\_source=chatgpt.com*](https://arxiv.org/abs/2608.02672?utm_source=chatgpt.com)

[*\[6\]*](https://arxiv.org/abs/2608.28021?utm_source=chatgpt.com) Compared to What? A Human-Anchored Security Benchmark for LLM-Generated Infrastructure-as-Code

[*https://arxiv.org/abs/2608.28021?utm\_source=chatgpt.com*](https://arxiv.org/abs/2608.28021?utm_source=chatgpt.com)

[*\[7\]*](https://huggingface.co/datasets/iac-eval-v2/iac-eval-v2?utm_source=chatgpt.com) iac-eval-v2/iac-eval-v2 · Datasets at Hugging Face

[*https://huggingface.co/datasets/iac-eval-v2/iac-eval-v2?utm\_source=chatgpt.com*](https://huggingface.co/datasets/iac-eval-v2/iac-eval-v2?utm_source=chatgpt.com)

[*\[8\]*](https://github.com/mchittineni/iacsecbench?utm_source=chatgpt.com) GitHub \- mchittineni/iacsecbench: An Open Framework and Empirical Benchmark for Evaluating Infrastructure-as-Code Security Gates · GitHub

[*https://github.com/mchittineni/iacsecbench?utm\_source=chatgpt.com*](https://github.com/mchittineni/iacsecbench?utm_source=chatgpt.com)

[*\[9\]*](https://scikit-learn.org/dev/modules/generated/sklearn.metrics.ndcg_score.html?utm_source=chatgpt.com) ndcg\_score — scikit-learn 1.10.dev0 documentation

[*https://scikit-learn.org/dev/modules/generated/sklearn.metrics.ndcg\_score.html?utm\_source=chatgpt.com*](https://scikit-learn.org/dev/modules/generated/sklearn.metrics.ndcg_score.html?utm_source=chatgpt.com)

[*\[10\]*](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.OneHotEncoder?utm_source=chatgpt.com) OneHotEncoder — scikit-learn 1.9.1 documentation

[*https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.OneHotEncoder?utm\_source=chatgpt.com*](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.OneHotEncoder?utm_source=chatgpt.com)

[*\[11\]*](https://scikit-learn.org/1.8/modules/generated/sklearn.impute.SimpleImputer.html?utm_source=chatgpt.com) SimpleImputer — scikit-learn 1.8.0 documentation

[*https://scikit-learn.org/1.8/modules/generated/sklearn.impute.SimpleImputer.html?utm\_source=chatgpt.com*](https://scikit-learn.org/1.8/modules/generated/sklearn.impute.SimpleImputer.html?utm_source=chatgpt.com)

[*\[13\]* *\[21\]* *\[24\]*](https://scikit-learn.org/dev/modules/generated/sklearn.ensemble.RandomForestRegressor.html?utm_source=chatgpt.com) RandomForestRegressor — scikit-learn 1.10.dev0 documentation

[*https://scikit-learn.org/dev/modules/generated/sklearn.ensemble.RandomForestRegressor.html?utm\_source=chatgpt.com*](https://scikit-learn.org/dev/modules/generated/sklearn.ensemble.RandomForestRegressor.html?utm_source=chatgpt.com)

[*\[14\]*](https://scikit-learn.org/dev/modules/generated/sklearn.model_selection.GroupKFold.html?utm_source=chatgpt.com) GroupKFold — scikit-learn 1.10.dev0 documentation

[*https://scikit-learn.org/dev/modules/generated/sklearn.model\_selection.GroupKFold.html?utm\_source=chatgpt.com*](https://scikit-learn.org/dev/modules/generated/sklearn.model_selection.GroupKFold.html?utm_source=chatgpt.com)

[*\[15\]*](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.spearmanr.html?utm_source=chatgpt.com) spearmanr — SciPy v1.18.0 Manual

[*https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.spearmanr.html?utm\_source=chatgpt.com*](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.spearmanr.html?utm_source=chatgpt.com)

[*\[16\]* *\[25\]*](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.wilcoxon.html) wilcoxon — SciPy v1.18.0 Manual

[*https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.wilcoxon.html*](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.wilcoxon.html)

[*\[17\]*](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html?utm_source=chatgpt.com) bootstrap — SciPy v1.18.0 Manual

[*https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html?utm\_source=chatgpt.com*](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html?utm_source=chatgpt.com)

[*\[18\]*](https://scikit-learn.org/1.0/modules/permutation_importance.html?utm_source=chatgpt.com) 4.2. Permutation feature importance — scikit-learn 1.0.2 documentation

[*https://scikit-learn.org/1.0/modules/permutation\_importance.html?utm\_source=chatgpt.com*](https://scikit-learn.org/1.0/modules/permutation_importance.html?utm_source=chatgpt.com)

[*\[19\]*](https://pypi.org/project/checkov/3.3.17/?utm_source=chatgpt.com) checkov · PyPI

[*https://pypi.org/project/checkov/3.3.17/?utm\_source=chatgpt.com*](https://pypi.org/project/checkov/3.3.17/?utm_source=chatgpt.com)

[*\[20\]*](https://developer.hashicorp.com/terraform/tutorials/cli/init?utm_source=chatgpt.com) Initialize Terraform configuration | Terraform | HashiCorp Developer

[*https://developer.hashicorp.com/terraform/tutorials/cli/init?utm\_source=chatgpt.com*](https://developer.hashicorp.com/terraform/tutorials/cli/init?utm_source=chatgpt.com)

# Implementation Design

# **Implementation Design — Thiết kế Implementation**

## **1\. Mục đích của Implementation Design**

Implementation Design mô tả cách chuyển **research methodology** của đề tài thành một hệ thống phần mềm có thể triển khai, chạy lại và đánh giá được.

Implementation không nhằm xây dựng một nền tảng DevSecOps hoàn chỉnh. Mục tiêu là tạo một **research pipeline tối thiểu nhưng reproducible**, hỗ trợ:

1. Thu thập và quản lý Terraform artifacts.  
2. Validate Terraform.  
3. Scan bằng Checkov.  
4. Chuẩn hóa security findings.  
5. Biểu diễn infrastructure context và scenario/business context.  
6. Tạo feature dataset.  
7. Quản lý human ground-truth ranking.  
8. Chạy các baseline.  
9. Train và inference bằng Random Forest.  
10. Tạo priority score và ranked findings.  
11. Đánh giá kết quả thực nghiệm.  
12. Xuất kết quả sang Security Gate dạng CLI/JSON.

Scope kỹ thuật được giữ ở **AWS \+ Terraform \+ Checkov \+ static analysis**, không triển khai thật lên AWS và không sử dụng runtime LLM. Random Forest là mô hình ML chính; XGBoost chỉ là optional extension.

---

# **2\. Implementation Principles**

Implementation tuân theo các nguyên tắc sau.

### **2.1 Research first, prototype second**

Code tồn tại để phục vụ câu hỏi nghiên cứu và experiment.

Không thêm component chỉ để hệ thống trông giống một production platform.

Ưu tiên:

**correctness → reproducibility → experimentability → simplicity**

thay vì:

**UI → microservices → cloud deployment → production scalability**

---

### **2.2 Modular nhưng không over-engineering**

Pipeline nên chia thành các module có trách nhiệm rõ ràng:

Terraform Corpus  
       ↓  
Terraform Validator  
       ↓  
Checkov Scanner  
       ↓  
Finding Normalizer  
       ↓  
Context Processor  
       ↓  
Feature Builder  
       ↓  
Research Dataset  
       ↓  
 ┌───────────────┬───────────────────┬────────────────┐  
 │ Severity      │ Contextual Rule   │ Random Forest  │  
 │ Baseline      │ Baseline          │ ML Model       │  
 └───────────────┴───────────────────┴────────────────┘  
                         ↓  
                 Priority Rankings  
                         ↓  
                 Evaluation Engine  
                         ↓  
                  Research Results  
                         ↓  
                Security Gate Prototype

Không cần microservices. Một Python project dạng modular monolith là đủ cho thesis này.

---

# **3\. High-Level Implementation Architecture**

Implementation được chia thành 7 logical layers.

┌─────────────────────────────────────────────┐  
│ L1 — DATA / CORPUS                          │  
│ Terraform \+ provenance \+ scenario metadata  │  
└────────────────────┬────────────────────────┘  
                     ↓  
┌─────────────────────────────────────────────┐  
│ L2 — SECURITY ANALYSIS                      │  
│ Terraform validate → Checkov                │  
└────────────────────┬────────────────────────┘  
                     ↓  
┌─────────────────────────────────────────────┐  
│ L3 — DATA PROCESSING                        │  
│ Normalize → Context → Feature Engineering   │  
└────────────────────┬────────────────────────┘  
                     ↓  
┌─────────────────────────────────────────────┐  
│ L4 — RESEARCH DATASET                       │  
│ Features \+ Ground Truth \+ Family Metadata   │  
└────────────────────┬────────────────────────┘  
                     ↓  
┌─────────────────────────────────────────────┐  
│ L5 — PRIORITIZATION                         │  
│ Severity | Context Rule | Random Forest     │  
└────────────────────┬────────────────────────┘  
                     ↓  
┌─────────────────────────────────────────────┐  
│ L6 — EVALUATION                             │  
│ NDCG | Spearman | Statistical Analysis      │  
└────────────────────┬────────────────────────┘  
                     ↓  
┌─────────────────────────────────────────────┐  
│ L7 — PROTOTYPE                              │  
│ Ranked Findings → Security Gate → CLI/JSON  │  
└─────────────────────────────────────────────┘

Kiến trúc này cố tình giữ research pipeline độc lập với prototype Security Gate. Security Gate là output consumer của prioritization pipeline, không phải trung tâm của nghiên cứu. Tài liệu v2.3 cũng xác định Security Gate là prototype vận hành chứ không phải một “scientific oracle”.

---

# **4\. Layer 1 — Corpus & Scenario Management**

## **4.1 Terraform Corpus**

Hệ thống cần quản lý các Terraform artifacts được chọn từ Source Corpus và Research Corpus.

Mỗi artifact/scenario nên có identifier ổn định.

Ví dụ:

family\_id  
scenario\_id  
source\_id  
source\_path  
context\_id

`family_id` đặc biệt quan trọng vì nó được sử dụng để ngăn data leakage khi train/test split.

Theo protocol v2.3, Research Corpus được lọc từ nguồn có provenance phù hợp và tập trung vào AWS Terraform có thể validate/scan bằng Checkov.

---

## **4.2 Đề xuất cấu trúc corpus**

data/  
├── source/  
│   ├── family\_001/  
│   │   ├── terraform/  
│   │   └── provenance.json  
│   └── ...  
│  
├── scenarios/  
│   ├── scenario\_001/  
│   │   └── context.json  
│   └── ...  
│  
└── processed/

Ví dụ `context.json`:

{  
  "scenario\_id": "scenario\_001\_prod",  
  "family\_id": "family\_001",  
  "environment": "production",  
  "asset\_criticality": "high",  
  "data\_sensitivity": "high"  
}

Các giá trị cụ thể và encoding phải được freeze trong data dictionary trước khi tạo benchmark chính.

---

# **5\. Layer 2 — Terraform Validation & Security Scanning**

## **5.1 Terraform Validator**

Module này kiểm tra Terraform artifact trước khi đưa vào security scanning.

Conceptual interface:

Terraform Artifact  
        ↓  
terraform validate  
        ↓  
Validation Result

Output nên lưu:

scenario\_id  
family\_id  
validation\_status  
validation\_error  
terraform\_version  
timestamp

Artifact không validate được không nên âm thầm đưa tiếp vào dataset.

Nó phải được:

* ghi log;  
* đánh dấu trạng thái;  
* xử lý theo failure policy đã freeze.

---

## **5.2 Checkov Scanner**

Terraform hợp lệ được scan bằng Checkov.

Workflow v2.3 yêu cầu version được pin để bảo đảm reproducibility; version được sử dụng trong workflow là **Checkov 3.3.17**.

Conceptual flow:

Validated Terraform  
        ↓  
Checkov 3.3.17  
        ↓  
Raw Checkov JSON

Raw scanner output phải được lưu lại thay vì chỉ giữ processed result.

Ví dụ:

artifacts/  
└── scans/  
    ├── scenario\_001\_checkov.json  
    ├── scenario\_002\_checkov.json  
    └── ...

Điều này giúp sau này có thể kiểm tra:

> Finding này thực sự đến từ scanner hay do normalization code tạo sai?

---

# **6\. Layer 3 — Finding Normalization**

Raw Checkov output không nên được đưa trực tiếp vào ML.

Cần một `Finding Normalizer`.

Checkov JSON  
      ↓  
Finding Normalizer  
      ↓  
Normalized Findings

Workflow v2.3 đã xác định bước normalization riêng trong pipeline.

Mỗi record đại diện cho:

> **one security finding in one contextual scenario**

Ví dụ conceptual schema:

finding\_id  
family\_id  
scenario\_id

check\_id  
resource\_address  
normalized\_resource\_address  
resource\_type

security\_category  
misconfiguration\_type

scanner\_severity  
scanner\_metadata

source\_file  
source\_line

Cần lưu ý:

> Một Checkov finding là một **scanner finding**, không được mặc định diễn giải thành một independent vulnerability.

Nhiều findings có thể liên quan đến cùng một root cause. Protocol v2.3 yêu cầu giới hạn này phải được nêu rõ khi diễn giải kết quả.

---

# **7\. Severity Mapping Component**

Pilot cho thấy Checkov có thể trả về:

severity \= None

Do đó không được viết code với giả định rằng Checkov luôn cung cấp severity.

Workflow v2.3 yêu cầu một severity mapping/policy riêng phải được xác định và freeze trước evaluation.

Implementation nên tách nó thành:

config/  
└── severity\_mapping.yaml

Conceptual interface:

Checkov Finding  
      ↓  
Frozen Severity Mapping  
      ↓  
Mapped Severity

Quan trọng:

**Severity mapping không được thay đổi sau khi xem kết quả của Random Forest chỉ để làm baseline mạnh hoặc yếu hơn.**

File mapping cần được version-control để experiment có thể reproduce.

---

# **8\. Context Processing**

Context được chia thành hai nhóm chính.

## **8.1 Scenario / Business Context**

Ví dụ:

environment  
asset\_criticality  
data\_sensitivity

Đây là metadata của scenario.

Ví dụ:

{  
  "environment": "production",  
  "asset\_criticality": "high",  
  "data\_sensitivity": "high"  
}

Context A/B trong protocol cũng sử dụng cách thay đổi contextual metadata trong khi Terraform giữ nguyên hoặc tương đương.

---

## **8.2 Finding / Infrastructure Context**

Các thuộc tính có thể bao gồm:

internet\_exposure  
privilege\_impact  
reachability  
public\_access  
wildcard\_action  
wildcard\_resource  
encryption\_missing  
logging\_missing

Nhưng feature chỉ được tạo khi có thể suy ra một cách khách quan từ:

* Terraform;  
* scanner result;  
* explicit scenario metadata.

Không được tạo feature dựa trên human rank.

Protocol yêu cầu finding-level features phải được xác định trước annotation để tránh target leakage.

---

# **9\. Feature Builder**

`Feature Builder` chuyển normalized findings \+ context thành ML-ready dataset.

Normalized Finding  
        \+  
Infrastructure Context  
        \+  
Scenario Context  
        ↓  
Feature Builder  
        ↓  
Feature Vector X

Ví dụ conceptual row:

environment \= production  
asset\_criticality \= high  
data\_sensitivity \= high  
internet\_exposure \= true  
privilege\_impact \= high  
reachability \= true  
resource\_type \= aws\_security\_group  
...

Feature schema phải được freeze trước main experiment.

---

## **9.1 Categorical encoding**

Các categorical features như:

environment  
asset\_criticality  
data\_sensitivity  
resource\_type

cần được encode thành representation mà model có thể sử dụng.

Đề xuất implementation đơn giản:

categorical feature  
        ↓  
One-Hot Encoding  
        ↓  
numeric columns

Không cần embedding hoặc neural-network-based representation.

---

## **9.2 Missing values**

Không nên tự động biến missing thành một giá trị có ý nghĩa security.

Ví dụ:

internet\_exposure \= unknown

không nhất thiết đồng nghĩa:

internet\_exposure \= false

Cần freeze policy:

missing  
unknown  
not\_applicable  
false

để tránh làm thay đổi semantic của feature.

---

## **9.3 `check_id` leakage / memorization**

`check_id` cần được xử lý đặc biệt.

Protocol v2.3 cảnh báo rằng model có thể học trực tiếp identity của Checkov rule thay vì học contextual prioritization.

Vì vậy implementation nên hỗ trợ ít nhất:

feature\_set\_without\_check\_id

và nếu thời gian cho phép:

feature\_set\_with\_check\_id

để thực hiện ablation/sensitivity analysis.

Không nên mặc định xem `check_id` là một core contextual feature.

---

# **10\. Ground Truth Data Layer**

Human annotation phải được lưu riêng khỏi machine-generated features.

Đề xuất:

annotations/  
└── ground\_truth.csv

Conceptual schema:

scenario\_id  
finding\_id  
human\_rank  
relevance\_grade  
annotation\_notes  
annotator\_id  
annotation\_version

Human ground truth được tạo theo ranking trong từng scenario. Annotation procedure và separation khỏi model result là thành phần quan trọng của protocol.

NDCG relevance mapping đã được xác định:

Rank 1 → 3  
Rank 2 → 2  
Rank 3 → 1  
Rank 4+ → 0  
---

## **10.1 Training target cần freeze**

Một điểm implementation **không nên tự quyết định** là exact target encoding cho `RandomForestRegressor`.

Các tài liệu đã xác định:

* human ranking;  
* relevance mapping phục vụ NDCG;  
* Random Forest tạo continuous priority score.

Nhưng implementation cần freeze rõ model được train trên:

human\_rank

hay:

relevance\_grade

hay một:

transformed priority target

trước main experiment.

Do đó code nên sử dụng configuration thay vì hard-code:

training:  
  target\_encoding: TBD\_BEFORE\_MAIN\_EXPERIMENT

Chỉ sau khi methodology freeze thì giá trị này mới được khóa.

Không được thử nhiều target encoding rồi chọn cái cho kết quả đẹp nhất nếu điều đó không được protocol cho phép.

---

# **11\. Research Dataset Builder**

Sau khi có:

normalized findings  
\+  
features  
\+  
ground truth

Dataset Builder tạo research-ready dataset.

features.csv  
      \+  
ground\_truth.csv  
      ↓  
Dataset Builder  
      ↓  
research\_dataset.csv

Dataset cuối cần giữ metadata như:

finding\_id  
scenario\_id  
family\_id

ngay cả khi các field này không được đưa vào model.

Lý do là chúng cần cho:

* grouping;  
* evaluation;  
* leakage checking;  
* traceability.

---

# **12\. Train/Test Split Manager**

Không sử dụng random row split đơn giản.

Split phải dựa trên:

family\_id

để findings thuộc cùng một Terraform/scenario family không xuất hiện ở cả training và testing.

Protocol v2.3 yêu cầu family-based splitting và đề xuất GroupKFold hoặc Leave-One-Family-Out.

Implementation:

Research Dataset  
       ↓  
Group Split by family\_id  
       ↓  
┌────────────────┬────────────────┐  
│ Train Families │ Test Families  │  
└────────────────┴────────────────┘

Nếu có Context A/B:

family\_017\_context\_A  
family\_017\_context\_B

cả hai phải nằm cùng một partition.

Ví dụ:

TRAIN:  
family\_001  
family\_002  
family\_003

TEST:  
family\_004  
family\_005

không được:

TRAIN: family\_004\_context\_A  
TEST:  family\_004\_context\_B  
---

# **13\. Prioritization Engines**

Hệ thống triển khai ba prioritization engines chính.

## **13.1 Severity Baseline**

Finding  
   ↓  
Frozen Severity Mapping  
   ↓  
Severity Score  
   ↓  
Ranking

Output:

finding\_id  
severity\_score  
severity\_rank  
---

## **13.2 Deterministic Contextual Baseline**

Feature Vector  
      ↓  
Frozen Contextual Scoring Policy  
      ↓  
Context Score  
      ↓  
Ranking

Conceptual function:

P\_context \= g(X)

Scoring policy phải được freeze trước khi nhìn vào final model results.

Baseline này rất quan trọng vì nó giúp kiểm tra:

> Có thực sự cần ML hay một contextual rule đơn giản đã đủ?

Workflow v2.3 xác định severity-only và deterministic contextual scoring là các baseline chính trước khi so sánh với Random Forest.

---

## **13.3 Random Forest Prioritizer**

ML pipeline:

Training Dataset  
      ↓  
Preprocessing  
      ↓  
RandomForestRegressor  
      ↓  
Trained Model

Inference:

Finding Features  
      ↓  
Same Preprocessing  
      ↓  
Random Forest  
      ↓  
Continuous Priority Score  
      ↓  
Sort Descending  
      ↓  
Priority Ranking

Random Forest là mô hình ML chính của workflow.

Output:

finding\_id  
ml\_priority\_score  
ml\_rank  
---

# **14\. Model Serialization**

Sau training, model nên được lưu thành artifact.

Đề xuất:

artifacts/  
└── models/  
    ├── rf\_model.joblib  
    ├── preprocessing.joblib  
    ├── feature\_schema.json  
    └── training\_metadata.json

`training_metadata.json` nên chứa:

experiment\_id  
dataset\_version  
feature\_version  
split\_version  
random\_seed  
model\_parameters  
training\_target  
timestamp

Nhờ vậy có thể trả lời:

> Model trong bảng kết quả thesis được train từ dataset/config nào?

---

# **15\. XGBoost Extension**

XGBoost không nằm trên critical path.

Nếu core experiment hoàn thành sớm:

Research Dataset  
      ↓  
XGBoost  
      ↓  
Priority Score  
      ↓  
Ranking

có thể được thêm như một supplementary experiment.

Workflow v2.3 xác định XGBoost là optional.

Do đó repository nên cho phép thêm model mới thông qua interface chung nhưng không cần xây framework plugin phức tạp.

Conceptual interface:

fit(X\_train, y\_train)  
predict(X\_test)  
save(path)  
load(path)  
---

# **16\. Evaluation Engine**

Evaluation Engine nhận:

Predicted Rankings  
        \+  
Human Ground Truth  
        ↓  
Evaluation

Các metric chính theo protocol:

Primary:  
NDCG@3  
NDCG@5

Secondary:  
Spearman correlation

Diagnostic:  
MAE  
RMSE

Evaluation phải thực hiện ở scenario level trước khi aggregate.

Ví dụ output:

scenario\_id  
method  
ndcg\_3  
ndcg\_5  
spearman  
mae  
rmse

Sau đó:

Scenario Metrics  
      ↓  
Aggregate  
      ↓  
Mean / Median  
      ↓  
Paired Statistical Comparison

Khi sample size hỗ trợ, protocol đề xuất paired scenario-level analysis, Wilcoxon, effect size và bootstrap 95% confidence interval.

---

# **17\. Contrastive Context Analyzer — Secondary**

Nếu B2 được giữ trong final scope, cần một module riêng để kiểm tra context sensitivity.

Concept:

Same / Equivalent Terraform

Context A  
dev / low criticality / low sensitivity

             VS

Context B  
prod / high criticality / high sensitivity

Matched finding dựa trên:

check\_id  
\+  
normalized\_resource\_address

Sau đó:

Δscore \= score\_B \- score\_A

và aggregate ở family level.

Protocol v2.3 mô tả contrastive analysis theo cách này.

Module này là secondary experiment, không nên chặn completion của core B1 experiment.

---

# **18\. Explainability / Model Inspection**

Không cần xây một XAI subsystem phức tạp.

Đề xuất mức tối thiểu:

Random Forest  
      ↓  
Feature Importance  
      ↓  
Permutation Importance  
      ↓  
Minimal Ablation

Mục tiêu không phải để tuyên bố causal relationship.

Mục tiêu là hỗ trợ câu hỏi:

> Model đang dựa nhiều vào nhóm feature nào?

và:

> Model có phụ thuộc bất thường vào một feature identifier hay không?

Các kết quả này nên được trình bày dưới dạng exploratory analysis thay vì một RQ độc lập.

---

# **19\. Security Gate Prototype**

Sau khi có priority scores:

Terraform  
   ↓  
Checkov  
   ↓  
Normalize  
   ↓  
Context  
   ↓  
Prioritization  
   ↓  
Ranked Findings  
   ↓  
Security Gate

Security Gate áp dụng operational policy:

PASS  
WARN / REVIEW  
BLOCK

Tài liệu cho phép implementation tối thiểu bằng CLI/JSON; không yêu cầu dashboard hoặc full web application.

Ví dụ CLI:

\$ python main.py evaluate examples/scenario\_001

Security Gate: REVIEW

Top Priority Findings:  
1\. CKV\_XXX   score=0.87  
2\. CKV\_YYY   score=0.74  
3\. CKV\_ZZZ   score=0.51

Ví dụ JSON:

{  
  "scenario\_id": "scenario\_001",  
  "gate\_decision": "REVIEW",  
  "findings": \[  
    {  
      "finding\_id": "F001",  
      "priority\_score": 0.87,  
      "rank": 1  
    }  
  \]  
}

Các threshold của Gate phải được mô tả là **operational policy**, không phải scientific ground truth.

---

# **20\. Proposed Repository Structure**

Đây là cấu trúc implementation đề xuất; tên thư mục/module không phải yêu cầu bắt buộc của protocol.

project/  
│  
├── README.md  
├── requirements.txt  
├── configs/  
│   ├── experiment.yaml  
│   ├── features.yaml  
│   ├── severity\_mapping.yaml  
│   └── gate\_policy.yaml  
│  
├── data/  
│   ├── source/  
│   ├── scenarios/  
│   ├── raw\_scans/  
│   ├── normalized/  
│   ├── annotations/  
│   ├── processed/  
│   └── splits/  
│  
├── src/  
│   ├── validation/  
│   │   └── terraform\_validator.py  
│   │  
│   ├── scanner/  
│   │   └── checkov\_runner.py  
│   │  
│   ├── normalization/  
│   │   └── finding\_normalizer.py  
│   │  
│   ├── context/  
│   │   ├── scenario\_context.py  
│   │   └── infrastructure\_context.py  
│   │  
│   ├── features/  
│   │   └── feature\_builder.py  
│   │  
│   ├── dataset/  
│   │   ├── dataset\_builder.py  
│   │   └── group\_splitter.py  
│   │  
│   ├── baselines/  
│   │   ├── severity\_baseline.py  
│   │   └── contextual\_baseline.py  
│   │  
│   ├── models/  
│   │   ├── random\_forest.py  
│   │   └── xgboost\_model.py        \# optional  
│   │  
│   ├── evaluation/  
│   │   ├── ranking\_metrics.py  
│   │   ├── statistics.py  
│   │   └── contrastive.py  
│   │  
│   └── gate/  
│       └── security\_gate.py  
│  
├── scripts/  
│   ├── build\_corpus.py  
│   ├── scan\_all.py  
│   ├── build\_dataset.py  
│   ├── train.py  
│   ├── evaluate.py  
│   └── run\_gate.py  
│  
├── artifacts/  
│   ├── models/  
│   ├── predictions/  
│   ├── rankings/  
│   └── metrics/  
│  
├── tests/  
│  
└── results/  
    ├── tables/  
    └── figures/

Điểm quan trọng không phải tên folder mà là separation giữa:

RAW DATA  
    ↓  
PROCESSED DATA  
    ↓  
RESEARCH DATASET  
    ↓  
MODEL ARTIFACTS  
    ↓  
EXPERIMENT RESULTS  
---

# **21\. Configuration-Driven Experiments**

Không nên hard-code research decisions trực tiếp trong Python.

Ví dụ:

experiment:  
  id: B1\_RF\_001  
  seed: 42

scanner:  
  name: checkov  
  version: 3.3.17

features:  
  include\_check\_id: false

split:  
  strategy: group\_kfold  
  group\_column: family\_id

model:  
  type: random\_forest

evaluation:  
  metrics:  
    \- ndcg\_3  
    \- ndcg\_5  
    \- spearman

training:  
  target\_encoding: TBD\_BEFORE\_FREEZE

Cách này giúp experiment có thể reproduce và giảm nguy cơ thay đổi methodology vô tình trong lúc code.

---

# **22\. Logging & Traceability**

Mỗi finding nên có thể trace ngược:

Research Result  
      ↓  
Prediction  
      ↓  
Feature Row  
      ↓  
Normalized Finding  
      ↓  
Raw Checkov Finding  
      ↓  
Terraform Source

Do đó nên duy trì các identifier:

source\_id  
family\_id  
scenario\_id  
finding\_id  
experiment\_id

Một prediction không nên tồn tại mà không biết nó đến từ:

* Terraform nào;  
* scenario nào;  
* Checkov finding nào;  
* feature version nào;  
* model version nào.

---

# **23\. Reproducibility**

Implementation phải pin các dependency quan trọng và lưu experiment configuration.

Workflow yêu cầu reproducibility và version control cho các thành phần chính.

Tối thiểu cần lưu:

Terraform version  
Checkov version \= 3.3.17  
Python version  
Python dependencies  
dataset version  
feature schema version  
annotation version  
random seed  
split definition  
model hyperparameters  
experiment configuration

Một experiment nên có:

experiment\_id

ví dụ:

EXP\_B1\_RF\_V1

để kết quả trong thesis có thể liên kết với code và artifact tương ứng.

---

# **24\. Testing Strategy**

Không cần enterprise-level testing.

Nhưng một số component phải có test vì lỗi ở đây có thể làm sai toàn bộ kết quả nghiên cứu.

## **MUST test**

### **Normalization test**

Known Checkov JSON  
      ↓  
Normalizer  
      ↓  
Expected normalized finding

### **Context extraction test**

Kiểm tra các infrastructure features được extract đúng từ fixture Terraform.

### **Split leakage test**

Assert:

train\_family\_ids ∩ test\_family\_ids \= ∅

Đây nên là automated assertion.

### **Context A/B integrity test**

Assert:

A.family\_id \== B.family\_id

và cả hai không được nằm ở hai partitions khác nhau.

### **Metric test**

Sử dụng ranking nhỏ có expected NDCG đã biết để kiểm tra implementation.

### **Reproducibility test**

Cùng:

dataset  
config  
seed

phải tạo ra kết quả nhất quán trong giới hạn hợp lý.

---

# **25\. Error Handling**

Pipeline không nên silently ignore failure.

Ví dụ:

Terraform validation failed  
        ↓  
LOG \+ STATUS  
        ↓  
Do not continue silently  
Checkov execution failed  
        ↓  
LOG \+ STATUS  
Context unavailable  
        ↓  
UNKNOWN / MISSING  
        ↓  
Do not invent context  
Finding cannot be matched in Context A/B  
        ↓  
Mark unmatched  
        ↓  
Exclude from matched-pair analysis according to frozen policy

Protocol v2.3 có failure-handling riêng và không cho phép sửa dữ liệu/phương pháp chỉ để làm hypothesis thành công.

---

# **26\. Implementation Order**

Vì đây là đề tài của một sinh viên và ML không phải phần duy nhất, implementation nên theo dependency order.

PHASE 1  
Corpus  
  ↓  
Terraform validation  
  ↓  
Checkov  
  ↓  
Normalization

PHASE 2  
Context representation  
  ↓  
Feature extraction  
  ↓  
Human annotation dataset

PHASE 3  
Severity baseline  
  ↓  
Context baseline

PHASE 4  
Random Forest  
  ↓  
Priority scoring  
  ↓  
Ranking

PHASE 5  
NDCG / Spearman  
  ↓  
Statistical analysis

PHASE 6  
Security Gate CLI/JSON

PHASE 7 — only if time remains  
Contrastive analysis  
Feature ablation  
GitHub Actions  
XGBoost

Không nên bắt đầu bằng:

Dashboard  
↓  
API  
↓  
Docker  
↓  
Cloud  
↓  
GitHub Actions  
↓  
sau đó mới dataset

vì những thành phần đó không giải quyết research dependency chính.

---

# **27\. MUST / SHOULD / OPTIONAL Implementation**

## **MUST**

Phải hoàn thành để thesis có core experiment:

Terraform corpus management  
Terraform validation  
Checkov scanning  
Finding normalization  
Context representation  
Feature builder  
Ground-truth dataset  
Family-based splitting  
Severity baseline  
Deterministic contextual baseline  
Random Forest  
Priority scoring  
Ranking  
NDCG@3  
NDCG@5  
Basic result export  
Reproducibility configuration  
Minimal CLI/JSON output  
---

## **SHOULD**

Làm nếu core pipeline ổn định:

Spearman correlation  
Paired statistical analysis  
Feature importance  
Permutation importance  
Minimal ablation  
Contrastive Context A/B analysis  
Second-review annotation subset  
Automated leakage tests  
GitHub Actions integration  
---

## **OPTIONAL**

Chỉ thực hiện khi MUST \+ SHOULD quan trọng đã hoàn thành:

XGBoost  
Additional datasets  
Additional visualizations  
Additional model comparison  
PR integration  
Advanced statistical analysis  
---

# **28\. Explicitly Not Implemented**

Để chống scope creep, implementation không bao gồm:

Multi-cloud support  
Azure/GCP support  
Kubernetes  
Runtime LLM  
RAG  
MCP  
Multi-agent system  
LLM fine-tuning  
Transformer  
Deep Learning  
Reinforcement Learning  
Attack graph  
SIEM platform  
Autonomous remediation  
Real AWS production deployment  
Complex dashboard  
Full web application  
Microservice architecture  
Large-scale distributed ML  
Production DevSecOps platform

Các nội dung này đã được đặt ngoài phạm vi nghiên cứu trong protocol.

---

# **29\. Implementation Dependency Map**

Dependency quan trọng nhất của project là:

Terraform Corpus  
       ↓  
Valid Terraform  
       ↓  
Checkov Findings  
       ↓  
Normalized Findings  
       ↓  
Context Features  
       ↓  
Ground Truth  
       ↓  
Research Dataset  
       ↓  
Baselines  
       ↓  
Random Forest  
       ↓  
Predicted Rankings  
       ↓  
Evaluation  
       ↓  
Research Conclusions

Điều này có nghĩa:

> **Không có dataset đúng → ML không có ý nghĩa.**

và:

> **Không có ground truth đáng bảo vệ → metric không có ý nghĩa.**

Do đó implementation của model không nên bắt đầu trước khi schema của findings, context và ground truth đủ ổn định.

---

# **30\. Minimum Viable Implementation**

Phiên bản nhỏ nhất nhưng vẫn đủ phục vụ thesis:

AWS Terraform  
      ↓  
terraform validate  
      ↓  
Checkov 3.3.17  
      ↓  
Python Normalizer  
      ↓  
CSV Dataset  
      ↓  
Context Features  
      ↓  
Human Ranking  
      ↓  
Severity Baseline  
Context Rule Baseline  
Random Forest  
      ↓  
Priority Rankings  
      ↓  
NDCG@3 / NDCG@5  
      ↓  
Results CSV/JSON  
      ↓  
Simple Security Gate CLI

Không cần:

Database  
Web frontend  
REST API  
Cloud server  
Microservices  
Kubernetes  
LLM service

để trả lời các research questions chính.

---

# **31\. Definition of Done**

Implementation được xem là hoàn thành khi có thể chạy một quy trình reproducible:

1\. Load selected Terraform artifact  
2\. Validate Terraform  
3\. Run pinned Checkov scanner  
4\. Parse and normalize findings  
5\. Attach/extract context  
6\. Generate feature dataset  
7\. Join frozen human ground truth  
8\. Split dataset by family  
9\. Run severity baseline  
10\. Run contextual baseline  
11\. Train/evaluate Random Forest  
12\. Generate continuous priority scores  
13\. Convert scores into rankings  
14\. Calculate NDCG@3 / NDCG@5  
15\. Produce comparison results  
16\. Save experiment artifacts/configuration  
17\. Generate ranked findings in CLI/JSON form

Quan trọng hơn, một người khác phải có khả năng xác định:

Data nào được dùng?  
Checkov version nào?  
Feature nào được dùng?  
Ground truth version nào?  
Family split nào?  
Model configuration nào?  
Experiment nào tạo ra bảng kết quả nào?  
---

# **32\. Final Implementation Architecture**

                   ┌─────────────────────┐  
                    │ Terraform Corpus    │  
                    │ \+ Provenance        │  
                    └──────────┬──────────┘  
                               ↓  
                    ┌─────────────────────┐  
                    │ Terraform Validate  │  
                    └──────────┬──────────┘  
                               ↓  
                    ┌─────────────────────┐  
                    │ Checkov 3.3.17      │  
                    └──────────┬──────────┘  
                               ↓  
                    ┌─────────────────────┐  
                    │ Finding Normalizer  │  
                    └──────────┬──────────┘  
                               ↓  
               ┌───────────────┴────────────────┐  
               ↓                                ↓  
    ┌──────────────────────┐        ┌─────────────────────┐  
    │ Infrastructure Facts│        │ Scenario Context    │  
    └───────────┬──────────┘        └──────────┬──────────┘  
                └──────────────┬───────────────┘  
                               ↓  
                    ┌─────────────────────┐  
                    │ Feature Builder     │  
                    └──────────┬──────────┘  
                               ↓  
                    ┌─────────────────────┐  
                    │ Research Dataset    │  
                    │ \+ Human GroundTruth │  
                    │ \+ family\_id         │  
                    └──────────┬──────────┘  
                               ↓  
                    ┌─────────────────────┐  
                    │ Family-based Split  │  
                    └──────────┬──────────┘  
                               ↓  
           ┌───────────────────┼───────────────────┐  
           ↓                   ↓                   ↓  
┌──────────────────┐ ┌──────────────────┐ ┌─────────────────┐  
│ Severity         │ │ Contextual Rule  │ │ Random Forest   │  
│ Baseline         │ │ Baseline         │ │ ML              │  
└────────┬─────────┘ └────────┬─────────┘ └────────┬────────┘  
         └────────────────────┼────────────────────┘  
                              ↓  
                    ┌────────────────────┐  
                    │ Priority Rankings  │  
                    └─────────┬──────────┘  
                              ↓  
                    ┌────────────────────┐  
                    │ Evaluation         │  
                    │ NDCG / Spearman    │  
                    │ Statistics         │  
                    └─────────┬──────────┘  
                              ↓  
                 ┌────────────┴─────────────┐  
                 ↓                          ↓  
       ┌──────────────────┐       ┌──────────────────┐  
       │ Research Results │       │ Security Gate    │  
       │ Tables/Figures   │       │ CLI / JSON       │  
       └──────────────────┘       └──────────────────┘  
---

# **33\. Tóm tắt Implementation Design**

Implementation của đề tài không cần là một hệ thống lớn.

Có thể hiểu toàn bộ project bằng chuỗi:

**Terraform → Checkov → Normalize → Context → Features → Ground Truth → Baselines \+ Random Forest → Priority Score → Ranking → Evaluation → Security Gate.**

Trong đó:

* **Checkov** chịu trách nhiệm phát hiện security findings.  
* **Normalizer** biến scanner output thành dữ liệu nhất quán.  
* **Context Processor** biểu diễn deployment/business context.  
* **Feature Builder** tạo dữ liệu cho ML.  
* **Human Ground Truth** xác định priority ranking theo methodology của nghiên cứu.  
* **Severity Baseline** đại diện cách ưu tiên truyền thống.  
* **Contextual Baseline** kiểm tra liệu rules đơn giản đã đủ hay chưa.  
* **Random Forest** học hàm priority scoring từ dữ liệu.  
* **Evaluation Engine** kiểm tra ranking bằng NDCG và các metric bổ sung.  
* **Security Gate** minh họa cách research result có thể được sử dụng trong DevSecOps workflow.

Trọng tâm implementation không phải:

> “Xây một AI security platform.”

Mà là:

> **“Xây một research pipeline đủ đơn giản, reproducible và có kiểm soát để kiểm tra liệu contextual information và machine learning có giúp ưu tiên các security findings trong AI-generated Terraform hay không.”**

Đây là ranh giới implementation quan trọng nhất để giữ đề tài khả thi trong khoảng thời gian 8–10 tuần.

# Evaluation Plan \+ Threats to Validity

# **Evaluation Plan \+ Threats to Validity — Kế hoạch đánh giá**

## **1\. Mục đích của Evaluation Plan**

Evaluation Plan xác định cách kiểm tra một cách có hệ thống liệu **context-aware security prioritization** và **machine learning** có tạo ra ranking phù hợp hơn với human-defined contextual priority hay không.

Evaluation không nhằm chứng minh rằng Random Forest bắt buộc phải tốt hơn mọi phương pháp khác.

Mục tiêu là thực hiện một comparison có kiểm soát giữa:

Severity-only Baseline  
          vs  
Deterministic Contextual Baseline  
          vs  
Random Forest

và so sánh ranking của từng phương pháp với **human ground-truth ranking**.

Protocol v2.3 xác định negative result vẫn là một research result hợp lệ; methodology và data không được thay đổi chỉ để làm hypothesis thành công.

---

# **2\. Research Questions được đánh giá**

Evaluation phải trực tiếp phục vụ các Research Questions đã freeze trong protocol, thay vì đánh giá model bằng các metric không liên quan đến mục tiêu nghiên cứu.

| Research Question | Evaluation focus |
| ----- | ----- |
| **RQ1** | Phân tích các loại/pattern security misconfiguration trong evaluated AI-generated IaC corpus |
| **RQ2** | Context-aware prioritization so với severity-only prioritization |
| **RQ3** | Machine-learning prioritization so với deterministic context-aware scoring |

Các RQ chính được xác định trong Workflow v2.3.

Feature importance, ablation và model interpretation được xem là **exploratory/supporting analysis**, không cần tạo thêm một RQ chính.

---

# **3\. Evaluation Structure**

Evaluation được chia thành ba phần.

EVALUATION

├── A. Corpus Analysis  
│      └── RQ1  
│  
├── B1. Main Prioritization Experiment  
│      ├── Severity Baseline  
│      ├── Contextual Baseline  
│      └── Random Forest  
│             ↓  
│        Human Ground Truth  
│             ↓  
│        Ranking Metrics  
│      └── RQ2 \+ RQ3  
│  
└── B2. Contrastive Context Analysis  
       ├── Context A  
       ├── Context B  
       └── Δ Priority Score

B1 là experiment chính.

B2 là secondary analysis nhằm kiểm tra **context sensitivity** của prioritization mechanism, không nên thay thế B1. Protocol v2.3 tách contrastive analysis thành một phần riêng của evaluation.

---

# **4\. Evaluation Unit**

Đơn vị evaluation chính là:

> **một scenario chứa một tập security findings đã được human annotator ranking.**

Không nên tính metric bằng cách gom tất cả findings của tất cả scenarios thành một ranking toàn cục.

Conceptually:

Scenario 1  
Finding A  
Finding B  
Finding C  
Finding D  
Finding E

Human Ranking:  
A \> C \> B \> E \> D

Model Ranking:  
C \> A \> B \> D \> E

        ↓

Calculate NDCG for Scenario 1

Sau đó thực hiện tương tự cho các scenarios khác và aggregate scenario-level results.

Cách tiếp cận scenario-level cũng phù hợp với paired statistical comparison được quy định trong protocol.

---

# **5\. Ground Truth for Evaluation**

Ground truth là **human ranking trong từng scenario**.

Mỗi finding nhận một unique priority rank theo annotation procedure đã freeze.

Rank 1 \= highest contextual priority  
Rank 2 \= second highest  
Rank 3 \= third highest  
...

Human annotation phải được thực hiện độc lập với final model output; annotator không nên nhìn Random Forest prediction, final baseline comparison hoặc evaluation result trong lúc tạo ground truth. Protocol v2.3 xác định procedure và blinding này để giảm circularity và evaluation bias.

Ground truth trong thesis phải được mô tả chính xác là:

> **human-defined contextual security priority under the study methodology**

thay vì:

> “absolute real-world security risk.”

---

# **6\. Relevance Mapping for Ranking Evaluation**

Đối với NDCG, human rank được chuyển thành relevance grade theo mapping đã freeze:

Human Rank 1 → Relevance 3  
Human Rank 2 → Relevance 2  
Human Rank 3 → Relevance 1  
Human Rank 4+ → Relevance 0

Đây là mapping được quy định trong Research Protocol v2.3.

Ví dụ:

| Finding | Human Rank | Relevance |
| ----- | ----- | ----- |
| F1 | 1 | 3 |
| F2 | 2 | 2 |
| F3 | 3 | 1 |
| F4 | 4 | 0 |
| F5 | 5 | 0 |

Mapping này được sử dụng để đánh giá ranking bằng NDCG.

Nó không nên tự động được xem là training target của Random Forest trừ khi target encoding đó được freeze riêng trong methodology.

---

# **7\. Methods under Comparison**

Main experiment so sánh ba phương pháp.

| Method | Context used | Learning |
| ----- | ----- | ----- |
| Severity-only Baseline | Không hoặc tối thiểu | Không |
| Deterministic Contextual Baseline | Có | Không |
| Random Forest | Có | Có |

Workflow v2.3 xác định severity-only và deterministic contextual scoring là hai baseline chính trước khi đánh giá Random Forest.

Điều này tạo ra comparison logic:

Severity  
   ↓  
"Context có giúp không?"  
   ↓  
Contextual Rule  
   ↓  
"ML có thêm giá trị ngoài contextual rule không?"  
   ↓  
Random Forest

Nhờ đó, nếu Random Forest tốt hơn severity-only nhưng không tốt hơn contextual baseline, thesis vẫn có thể đưa ra một kết luận nghiên cứu có ý nghĩa.

---

# **8\. Dataset Split for Evaluation**

Không sử dụng random finding-level split.

Split phải dựa trên:

family\_id

để findings thuộc cùng một Terraform/scenario family không xuất hiện đồng thời ở train và test.

Protocol v2.3 yêu cầu family-based splitting và đề xuất các strategy như GroupKFold hoặc Leave-One-Family-Out.

Correct:

TRAIN  
family\_001  
family\_002  
family\_003

TEST  
family\_004  
family\_005

Incorrect:

TRAIN  
family\_004\_context\_A

TEST  
family\_004\_context\_B

Context A/B thuộc cùng family phải nằm trong cùng partition.

---

# **9\. Leakage Check trước Evaluation**

Trước khi chạy experiment chính, implementation phải kiểm tra:

train\_family\_ids ∩ test\_family\_ids \= ∅

Ngoài family leakage, cần kiểm tra feature leakage.

Đặc biệt, `check_id` có nguy cơ cho phép model ghi nhớ identity của scanner rule thay vì học contextual prioritization. Protocol v2.3 cảnh báo trực tiếp về khả năng memorization này.

Do đó main experiment nên có một feature configuration đã freeze; nếu `check_id` được nghiên cứu, nên xử lý thông qua controlled ablation/sensitivity analysis thay vì mặc định coi nó là một contextual feature.

---

# **10\. Primary Evaluation Metrics**

## **10.1 NDCG@3**

**Normalized Discounted Cumulative Gain at 3** đánh giá mức độ đúng của ranking ở ba vị trí đầu.

Đây là metric quan trọng vì trong security prioritization, DevSecOps thường quan tâm nhiều hơn đến:

> “Những findings cần xử lý đầu tiên có được đưa lên đầu ranking hay không?”

thay vì yêu cầu toàn bộ danh sách phải có thứ tự hoàn hảo.

Conceptually:

Human:  
A \> B \> C \> D \> E

Prediction:  
A \> C \> B \> E \> D

          ↓

NDCG@3  
---

## **10.2 NDCG@5**

NDCG@5 mở rộng evaluation đến top five findings.

Hai metric:

NDCG@3  
NDCG@5

là **primary ranking metrics** của protocol.

Các scenario phải đáp ứng điều kiện eligibility tương ứng trước khi được sử dụng cho một giá trị `@k`; không nên âm thầm coi scenario không đủ finding density là một observation tương đương.

---

# **11\. Secondary Metric — Spearman Correlation**

Spearman rank correlation được sử dụng để kiểm tra mức độ tương đồng của **overall ordering** giữa predicted ranking và human ranking.

Conceptually:

Human Ranking  
      ↕  
Predicted Ranking

Spearman ρ

Giá trị cao hơn biểu thị ordering tương đồng hơn.

Trong thiết kế nghiên cứu này:

NDCG@3 / NDCG@5  
        \=  
Primary evidence

Spearman  
        \=  
Secondary evidence

Spearman không thay thế NDCG vì research problem tập trung nhiều vào ưu tiên các findings ở đầu danh sách. Protocol xác định Spearman là secondary metric.

---

# **12\. Diagnostic Metrics — MAE / RMSE**

MAE và RMSE có thể được sử dụng như diagnostic metrics cho scoring/regression behavior.

MAE  
RMSE

không phải main success criteria của thesis.

Một model có regression error thấp chưa chắc tạo ra ranking tốt nhất.

Ví dụ:

Model A  
Low RMSE  
Poor top-3 ordering

Model B  
Higher RMSE  
Correct top-3 ordering

Đối với research question về prioritization, Model B có thể phù hợp hơn theo ranking metrics.

Vì vậy protocol đặt MAE/RMSE ở vai trò diagnostic thay vì primary evidence.

---

# **13\. Main Experiment B1**

Main experiment thực hiện cùng một evaluation procedure cho ba methods:

TEST SCENARIO  
      ↓  
┌───────────────┐  
│ Severity      │  
└───────┬───────┘  
        ↓  
Severity Ranking

TEST SCENARIO  
      ↓  
┌───────────────┐  
│ Context Rule  │  
└───────┬───────┘  
        ↓  
Context Ranking

TEST SCENARIO  
      ↓  
┌───────────────┐  
│ Random Forest │  
└───────┬───────┘  
        ↓  
ML Ranking

Mỗi ranking sau đó được so với:

Human Ground-Truth Ranking

để tạo:

NDCG@3  
NDCG@5  
Spearman  
MAE/RMSE where applicable  
---

# **14\. Scenario-Level Result Table**

Raw evaluation result nên được lưu ở scenario level.

Ví dụ:

| Scenario | Method | NDCG@3 | NDCG@5 | Spearman |
| ----- | ----- | ----- | ----- | ----- |
| S01 | Severity | ... | ... | ... |
| S01 | Context | ... | ... | ... |
| S01 | Random Forest | ... | ... | ... |
| S02 | Severity | ... | ... | ... |
| S02 | Context | ... | ... | ... |
| S02 | Random Forest | ... | ... | ... |

Sau đó mới aggregate.

Điều này giữ được paired structure:

Same Scenario

Severity  
Context  
Random Forest

thay vì so sánh các nhóm scenario khác nhau.

---

# **15\. Aggregate Evaluation**

Sau scenario-level evaluation, report có thể tổng hợp:

Mean  
Median  
Distribution  
Confidence Interval

cho từng method.

Ví dụ final comparison table:

| Method | NDCG@3 | NDCG@5 | Spearman |
| ----- | ----- | ----- | ----- |
| Severity | ... | ... | ... |
| Context Rule | ... | ... | ... |
| Random Forest | ... | ... | ... |

Các giá trị thực chỉ được điền sau experiment.

Không tạo expected numbers trước.

---

# **16\. Statistical Analysis**

Protocol v2.3 yêu cầu comparison theo paired scenario-level design và đề xuất:

Wilcoxon signed-rank test  
Effect size  
Bootstrap 95% confidence interval

khi sample size và dữ liệu hỗ trợ.

Comparison quan trọng nhất là:

RQ2:  
Contextual Baseline  
vs  
Severity Baseline

và:

RQ3:  
Random Forest  
vs  
Deterministic Contextual Baseline

P-value không nên được trình bày một mình.

Interpretation nên kết hợp:

Observed metric difference  
\+  
Effect size  
\+  
Confidence interval  
\+  
Statistical test  
\+  
Practical/security interpretation

Nếu dataset cuối quá nhỏ để statistical inference mạnh, thesis phải báo cáo limitation thay vì phóng đại statistical significance.

---

# **17\. Evaluation of RQ1 — Corpus Analysis**

RQ1 khác RQ2/RQ3 vì đây chủ yếu là **descriptive corpus analysis**, không phải model comparison.

Có thể report:

Misconfiguration categories  
Frequency of findings  
Resource types  
Finding density per scenario  
Distribution across corpus/families

Nhưng kết luận phải giới hạn ở:

> **evaluated AI-generated IaC corpus**

không được chuyển thành:

> “Generative AI nói chung thường tạo ra loại vulnerability X.”

Protocol v2.3 đặt RQ1 ở corpus analysis riêng.

---

# **18\. Contrastive Context Evaluation — B2**

B2 kiểm tra model/contextual prioritizer có phản ứng với sự thay đổi context hay không.

Thiết kế:

Same / Equivalent Terraform  
            │  
      ┌─────┴─────┐  
      ↓           ↓  
 Context A     Context B

 dev           production  
 low           high  
 low           high

Terraform giữ nguyên hoặc tương đương trong khi contextual metadata thay đổi theo thiết kế protocol.

Matched finding được xác định bằng:

check\_id  
\+  
normalized\_resource\_address

Sau đó:

Δscore \= score\_B \- score\_A

và aggregate ở family level.

B2 trả lời một câu hỏi khác với B1:

B1:  
Ranking có giống human priority không?

B2:  
Priority score có nhạy với contextual change không?

Không được diễn giải B2 đơn giản thành bằng chứng rằng Context B “thực sự nguy hiểm hơn” trong mọi tình huống.

Protocol cũng nhấn mạnh context không tự động quyết định ranking; Context A và B có thể có cùng hoặc khác ranking nếu rationale nhất quán.

---

# **19\. Exploratory Model Analysis**

Sau main evaluation có thể thực hiện:

Feature Importance  
Permutation Importance  
Minimal Feature Ablation

Mục tiêu là hỗ trợ interpretation:

> Model đang sử dụng nhóm contextual features nào?

Không dùng feature importance để tuyên bố:

> Feature X gây ra security risk.

Feature importance mô tả behavior của model trong dataset và experimental setting hiện tại, không chứng minh causality.

---

# **20\. Evaluation Sequence**

Main evaluation nên được thực hiện theo thứ tự:

Freeze Dataset  
       ↓  
Freeze Ground Truth  
       ↓  
Freeze Feature Schema  
       ↓  
Freeze Severity Mapping  
       ↓  
Freeze Contextual Baseline  
       ↓  
Freeze Family Split  
       ↓  
Train Random Forest  
       ↓  
Predict Test Data  
       ↓  
Generate Rankings  
       ↓  
Calculate Scenario Metrics  
       ↓  
Aggregate Results  
       ↓  
Statistical Analysis  
       ↓  
Exploratory Analysis  
       ↓  
Interpretation  
       ↓  
Threats to Validity

Điểm quan trọng là các research decisions không được điều chỉnh hậu nghiệm chỉ vì final results không đẹp.

---

# **21\. Interpretation Matrix**

Evaluation không sử dụng rule:

ML wins → thesis succeeds  
ML loses → thesis fails

Thay vào đó:

| Observed result | Research interpretation |
| ----- | ----- |
| Context \> Severity | Evidence trong benchmark rằng contextual information hỗ trợ prioritization |
| Context ≈ Severity | Context representation hiện tại chưa cho thấy measurable benefit |
| RF \> Context Rule | Evidence rằng learned nonlinear relationships có thể bổ sung giá trị ngoài deterministic rule |
| RF ≈ Context Rule | Simple contextual scoring có thể đủ cho dataset hiện tại |
| RF \< Context Rule | ML approach/configuration hiện tại không cải thiện deterministic baseline |
| All methods similar | Dataset, context representation hoặc task có thể chưa tạo đủ discriminative signal |

Các kết luận trên phải được diễn đạt theo dữ liệu thực tế và uncertainty của experiment, không phải như universal conclusions.

Negative result được protocol chấp nhận và không phải lý do để sửa annotation/data sau khi nhìn thấy kết quả.

---

# **22\. Success Criteria**

Research success không được định nghĩa là:

> “Random Forest phải đạt NDCG cao nhất.”

Project được xem là đạt mục tiêu nghiên cứu khi pipeline có thể:

Corpus  
   ↓  
Security Findings  
   ↓  
Context Representation  
   ↓  
Human Ground Truth  
   ↓  
Severity Baseline  
Context Baseline  
Random Forest  
   ↓  
Comparable Rankings  
   ↓  
NDCG / Spearman  
   ↓  
Evidence-based Analysis

và từ đó trả lời được RQ1, RQ2 và RQ3 trong phạm vi benchmark đã định nghĩa.

---

# **23\. Threats to Validity**

Threats to Validity phải được xem là một phần của research design, không phải chỉ là đoạn disclaimer ở cuối thesis.

Protocol v2.3 đã dành riêng phần threats to validity cho những giới hạn của dataset, annotation, scanner, contextual design, ML evaluation và khả năng generalize.

Các threat chính của đề tài được tổ chức thành:

Construct Validity  
Internal Validity  
External Validity  
Conclusion / Statistical Validity  
Reliability & Reproducibility  
---

# **24\. Construct Validity**

## **24.1 Human priority không phải absolute risk**

### **Threat**

Human annotation phản ánh priority theo methodology, context và rubric của nghiên cứu.

Nó không phải một measurement hoàn hảo của “true cyber risk”.

Nếu chỉ có một primary annotator, subjectivity càng đáng chú ý.

### **Mitigation**

Sử dụng annotation rubric đã freeze, ghi rationale, giữ ranking procedure nhất quán và nếu nguồn lực cho phép sử dụng second reviewer cho một subset.

Protocol cho phép thiết kế single annotator với limitation được công khai, đồng thời xem second annotator/reviewer là một biện pháp tăng độ tin cậy chứ không nhất thiết là dependency bắt buộc.

Trong thesis sử dụng thuật ngữ:

> **study-defined contextual priority**

thay vì:

> **objective real-world risk**.

---

## **24.2 Context-label circularity**

### **Threat**

Nếu annotator tạo ranking bằng đúng một công thức từ:

environment  
asset criticality  
data sensitivity  
internet exposure  
...

và Random Forest cũng nhận chính các features đó, model có thể chỉ học lại annotation rubric.

Khi đó kết quả tốt không nhất thiết chứng minh ML khám phá được một relationship mới.

### **Mitigation**

Human annotation phải dựa trên security reasoning theo rubric thay vì output trực tiếp của contextual baseline.

Deterministic contextual scoring phải được giữ như một baseline riêng.

Annotation phải được freeze trước final model evaluation.

---

## **24.3 Scanner finding ≠ independent vulnerability**

### **Threat**

Checkov có thể tạo nhiều findings liên quan đến cùng một underlying configuration/root cause.

Nếu mỗi finding được diễn giải là một vulnerability độc lập, kết quả có thể bị phóng đại.

### **Mitigation**

Unit of analysis phải được mô tả là:

> **scanner security finding**

và thesis phải công khai rằng findings không nhất thiết độc lập về root cause. Đây là limitation được protocol nêu trực tiếp.

---

## **24.4 Severity representation**

### **Threat**

Pilot cho thấy Checkov có thể trả `severity=None`.

Do đó severity-only baseline không thể mặc định dựa vào raw Checkov severity.

### **Mitigation**

Sử dụng một severity mapping/policy riêng và freeze nó trước final evaluation. Workflow v2.3 ghi nhận vấn đề này từ pilot.

Thesis phải nói rõ đây là study-defined severity mapping nếu mapping không phải raw scanner severity.

---

# **25\. Internal Validity**

## **25.1 Family leakage**

### **Threat**

Nếu findings của cùng Terraform family xuất hiện ở cả train và test, Random Forest có thể ghi nhớ pattern của family thay vì generalize.

Context A/B đặc biệt dễ gây leakage vì Terraform có thể giống nhau.

### **Mitigation**

Split theo `family_id`.

train\_family\_ids ∩ test\_family\_ids \= ∅

Context A/B của cùng family phải nằm cùng partition.

---

## **25.2 Feature leakage**

### **Threat**

Các feature được tạo sau annotation hoặc trực tiếp encode human rank có thể làm model nhìn thấy target.

### **Mitigation**

Finding-level features phải được derive **trước annotation** và không được lấy từ human rank. Protocol v2.3 quy định separation này.

---

## **25.3 `check_id` memorization**

### **Threat**

Random Forest có thể học:

CKV\_X → usually high  
CKV\_Y → usually low

thay vì học contextual relationships.

### **Mitigation**

Không mặc định đưa `check_id` vào core feature set.

Nếu nghiên cứu nó, sử dụng controlled ablation/sensitivity analysis và report rõ ảnh hưởng. Protocol đã cảnh báo vấn đề memorization của identifier-like features.

---

## **25.4 Annotation contamination**

### **Threat**

Nếu annotator nhìn thấy:

RF score  
context baseline score  
final metric

trước khi hoàn tất annotation, ground truth có thể bị ảnh hưởng bởi chính methods đang được đánh giá.

### **Mitigation**

Freeze annotation trước final model evaluation và giữ annotator blind với model predictions trong annotation procedure.

---

## **25.5 Post-hoc methodology changes**

### **Threat**

Sau khi thấy Random Forest không thắng, researcher có thể vô thức thay:

feature set  
severity mapping  
annotation  
baseline weights  
split  
metric

để cải thiện kết quả.

### **Mitigation**

Freeze methodology/configuration trước main evaluation và version-control mọi amendment.

Negative result phải được giữ và phân tích thay vì “sửa” experiment để tạo positive result.

---

# **26\. External Validity**

## **26.1 AWS-only scope**

Kết quả chỉ được đánh giá trên AWS Terraform trong scope hiện tại.

Không thể tự động generalize sang:

Azure  
GCP  
Kubernetes  
CloudFormation  
Pulumi  
Ansible  
---

## **26.2 Terraform-only scope**

Research chỉ đánh giá Terraform artifacts.

Kết quả không chứng minh rằng cùng methodology/model sẽ hoạt động tương đương với các IaC languages khác.

---

## **26.3 Checkov dependency**

Security findings đến từ Checkov.

Một scanner khác có thể:

detect different findings  
use different rules  
produce different metadata

Do đó conclusions chịu ảnh hưởng của scanner được lựa chọn.

---

## **26.4 Corpus representativeness**

Research Corpus được xây dựng từ các artifacts đáp ứng provenance, license, reproducibility và technical eligibility criteria.

Điều này tạo một selected corpus chứ không phải toàn bộ population của AI-generated Terraform. Dataset tiers và selection criteria được protocol định nghĩa rõ.

Vì vậy kết luận RQ1 phải dùng phrasing:

> “Within the evaluated corpus…”

thay vì:

> “All AI-generated Terraform…”

---

## **26.5 Static-analysis-only scope**

Project không deploy Terraform vào real AWS environment.

Do đó research không trực tiếp quan sát:

runtime behavior  
real attacks  
production incidents  
actual exploitability  
organizational impact

Conclusions chỉ thuộc phạm vi static IaC security prioritization.

---

# **27\. Conclusion / Statistical Validity**

## **27.1 Limited sample size**

### **Threat**

Số scenario/family có thể nhỏ do human annotation tốn thời gian.

Sample nhỏ làm statistical estimates không ổn định và confidence interval rộng.

### **Mitigation**

Ưu tiên:

effect size  
confidence interval  
scenario-level distribution  
paired comparison

thay vì chỉ dựa vào p-value.

Protocol sử dụng paired analysis, Wilcoxon, effect size và bootstrap confidence intervals để hỗ trợ interpretation.

---

## **27.2 NDCG eligibility**

### **Threat**

Không phải scenario nào cũng có đủ finding density cho mọi `NDCG@k`.

Nếu các scenario ít findings bị xử lý không nhất quán, aggregate result có thể gây hiểu nhầm.

### **Mitigation**

Freeze eligibility rule trước evaluation và report:

Total scenarios  
NDCG@3-eligible scenarios  
NDCG@5-eligible scenarios  
Excluded scenarios \+ reason

Không thay đổi eligibility sau khi thấy model results.

---

## **27.3 Metric dependence**

### **Threat**

Một metric duy nhất có thể tạo ra interpretation thiếu đầy đủ.

Ví dụ:

High NDCG@3  
but  
Lower overall Spearman

không phải contradiction; hai metric đang đo hai khía cạnh khác nhau.

### **Mitigation**

Dùng:

NDCG@3 / NDCG@5  
\+  
Spearman  
\+  
Diagnostic MAE/RMSE  
\+  
Scenario-level inspection

với vai trò metric được xác định trước.

---

# **28\. Reliability & Reproducibility**

### **Threat**

Kết quả có thể thay đổi do:

scanner version  
dependency version  
random seed  
data preprocessing  
feature encoding  
family split  
model hyperparameters

### **Mitigation**

Experiment phải lưu tối thiểu:

Terraform version  
Checkov version  
Python environment  
dependency versions  
dataset version  
annotation version  
feature schema  
severity mapping  
family split  
random seed  
model configuration  
experiment ID

Workflow v2.3 yêu cầu pin versions và lưu các artifacts cần thiết để reproduce experiment.

Checkov trong workflow hiện tại được pin ở version **3.3.17**.

---

# **29\. Threat-Mitigation Summary**

| Validity Type | Main Threat | Primary Mitigation |
| ----- | ----- | ----- |
| Construct | Human priority subjective | Frozen rubric \+ transparent limitation |
| Construct | Context-label circularity | Separate annotation and contextual baseline |
| Construct | Findings ≠ independent vulnerabilities | Interpret as scanner findings |
| Construct | Missing scanner severity | Frozen severity mapping |
| Internal | Family leakage | Group by `family_id` |
| Internal | Feature/target leakage | Features before annotation |
| Internal | `check_id` memorization | Exclude/ablate |
| Internal | Annotation contamination | Blind annotation |
| Internal | Post-hoc tuning | Freeze protocol/config |
| External | AWS-only | Limit claims |
| External | Terraform-only | Limit claims |
| External | Checkov dependency | Scanner-specific limitation |
| External | Selected corpus | No universal GenAI claims |
| External | Static analysis | No runtime-risk claims |
| Statistical | Small sample | Paired analysis \+ CI \+ effect size |
| Statistical | NDCG eligibility | Freeze and report eligibility |
| Statistical | Metric dependence | Multiple predefined metrics |
| Reliability | Version/config variation | Pin and version artifacts |

---

# **30\. Reporting Plan**

Final Results chapter nên có logical flow:

RQ1 — Corpus Characteristics  
        ↓  
RQ2 — Severity vs Context  
        ↓  
RQ3 — Context Rule vs Random Forest  
        ↓  
Contrastive Analysis  
        ↓  
Exploratory Feature Analysis  
        ↓  
Statistical Analysis  
        ↓  
Threats to Validity  
        ↓  
Interpretation

Mỗi comparison phải report cả result và limitation.

Ví dụ structure:

Observed result  
      ↓  
Metric evidence  
      ↓  
Statistical evidence  
      ↓  
Security interpretation  
      ↓  
Limitation  
      ↓  
Answer to RQ  
---

# **31\. What Not to Claim**

Evaluation không đủ cơ sở để tuyên bố:

"Random Forest detects vulnerabilities better than Checkov."

"ML measures true cyber risk."

"The model works for all Terraform."

"The model works for all cloud platforms."

"AI-generated Terraform is generally insecure."

"Context B is always more dangerous than Context A."

"The Security Gate can replace a security analyst."

Các claims phù hợp hơn có dạng:

> “Within the evaluated AWS Terraform benchmark and study-defined contextual prioritization setting…”

hoặc:

> “The observed results suggest that…”

hoặc:

> “No measurable improvement was observed under the current dataset and experimental design…”

Research boundary này phù hợp với scope và validity limitations của protocol.

---

# **32\. Definition of Done for Evaluation**

Evaluation được xem là hoàn thành khi có thể trace toàn bộ:

Human Ground Truth  
        ↓  
Frozen Test Scenarios  
        ↓  
Severity Ranking  
Context Ranking  
RF Ranking  
        ↓  
Scenario-Level Metrics  
        ↓  
NDCG@3  
NDCG@5  
Spearman  
        ↓  
Aggregate Results  
        ↓  
Statistical Comparison  
        ↓  
RQ Answers  
        ↓  
Threats to Validity

và có thể trả lời rõ:

RQ1:  
Những security misconfiguration patterns nào xuất hiện  
trong evaluated corpus?

RQ2:  
Context-aware prioritization khác/cải thiện như thế nào  
so với severity-only baseline trong benchmark?

RQ3:  
Random Forest có tạo measurable benefit nào  
so với deterministic contextual scoring hay không?

Câu trả lời cuối cùng phải dựa trên experiment thực tế, kể cả khi kết quả là:

YES  
NO  
MIXED  
INCONCLUSIVE

Không có yêu cầu khoa học rằng Random Forest phải thắng.

---

# **33\. Final Evaluation Framework**

                ┌──────────────────────┐  
                 │ Evaluated IaC Corpus │  
                 └──────────┬───────────┘  
                            ↓  
                 ┌──────────────────────┐  
                 │ Corpus Analysis      │  
                 │ RQ1                  │  
                 └──────────────────────┘

                 ┌──────────────────────┐  
                 │ Prioritization       │  
                 │ Benchmark            │  
                 └──────────┬───────────┘  
                            ↓  
                  ┌───────────────────┐  
                  │ Family-based Split│  
                  └─────────┬─────────┘  
                            ↓  
       ┌────────────────────┼────────────────────┐  
       ↓                    ↓                    ↓  
┌──────────────┐    ┌───────────────┐    ┌──────────────┐  
│ Severity     │    │ Context Rule  │    │ Random Forest│  
│ Baseline     │    │ Baseline      │    │              │  
└──────┬───────┘    └───────┬───────┘    └──────┬───────┘  
       │                    │                    │  
       ↓                    ↓                    ↓  
 Severity Rank         Context Rank           ML Rank  
       │                    │                    │  
       └────────────────────┼────────────────────┘  
                            ↓  
                 ┌──────────────────────┐  
                 │ Human Ground Truth   │  
                 └──────────┬───────────┘  
                            ↓  
                 ┌──────────────────────┐  
                 │ NDCG@3 / NDCG@5     │  
                 │ Spearman             │  
                 │ MAE/RMSE diagnostic │  
                 └──────────┬───────────┘  
                            ↓  
                 ┌──────────────────────┐  
                 │ Paired Comparison    │  
                 │ Effect Size / CI     │  
                 │ Wilcoxon if suitable│  
                 └──────────┬───────────┘  
                            ↓  
                 ┌──────────────────────┐  
                 │ RQ2 / RQ3 Answers    │  
                 └──────────┬───────────┘  
                            ↓  
                 ┌──────────────────────┐  
                 │ Threats to Validity  │  
                 └──────────┬───────────┘  
                            ↓  
                 ┌──────────────────────┐  
                 │ Research Conclusion  │  
                 └──────────────────────┘  
---

# **34\. Tóm tắt**

Evaluation của đề tài có thể được nhớ bằng công thức:

> **Same test scenarios \+ same human ground truth \+ three prioritization methods \+ ranking metrics \+ paired analysis.**

Trong đó:

**RQ1** được trả lời bằng descriptive corpus analysis.

**RQ2** được trả lời bằng:

> Severity-only vs Context-aware baseline.

**RQ3** được trả lời bằng:

> Deterministic contextual baseline vs Random Forest.

**NDCG@3 và NDCG@5** là primary metrics.

**Spearman** là secondary metric.

**MAE/RMSE** chỉ đóng vai trò diagnostic.

**Wilcoxon \+ effect size \+ bootstrap confidence interval** được sử dụng cho paired statistical analysis khi dữ liệu hỗ trợ.

Và nguyên tắc quan trọng nhất:

> **Evaluation phải kiểm tra hypothesis, không được thiết kế để bảo đảm ML thắng.**

Nếu Random Forest không vượt deterministic contextual baseline, đó vẫn là một kết quả nghiên cứu có giá trị nếu dataset, ground truth, split, metrics và experimental procedure được xây dựng đúng và được báo cáo minh bạch.

# Project Plan — Kế hoạch thực hiện

# **Kế hoạch thực hiện thực tế cho luận văn: Context-Aware ML for Security Risk Prioritization of GenAI-Generated Terraform**

## **Tóm tắt điều hành**

Với các ràng buộc thực tế — **một sinh viên ngành Network & Security, chưa học Machine Learning, khoảng 10 tuần làm việc chủ động và phải giữ tối thiểu 2 tuần dự phòng** — phương án an toàn nhất không phải là cố đạt toàn bộ quy mô “40–60 families / 80–120 contextual scenarios / ≥300 findings” ngay từ đầu. Research Protocol v2.3 tự xác định các con số đó là **planning targets, không phải hard requirements**, đồng thời đặt chất lượng benchmark, finding density, category/resource/family diversity và NDCG@5 eligibility cao hơn raw sample count. fileciteturn0file0

Kế hoạch tối ưu cho hoàn cảnh của bạn là:

**10 tuần active work ≈ 326 giờ có kế hoạch \+ 2 tuần buffer không dùng để mở scope.**

Critical path nên là:

Freeze methodology  
     	↓  
 Acquire / screen corpus  
     	↓  
 Validate \+ Checkov scan  
     	↓  
 Normalize \+ extract context features  
     	↓  
 Freeze benchmark  
     	↓  
 Human annotation  
     	↓  
 Freeze ground truth \+ family split  
     	↓  
 Severity baseline \+ Context baseline  
     	↓  
 Random Forest  
     	↓  
 NDCG / Spearman / Statistics  
     	↓  
 Clean reproduction run  
     	↓  
 Thesis \+ Demo \+ Defense

Security Gate là **prototype sau research core**, còn XGBoost là optional. Đây chính là nguyên tắc “research first, prototype second” của blueprint và workflow hiện tại. fileciteturn0file1 fileciteturn0file2

Điểm quan trọng nhất của kế hoạch này là **không dành phần lớn thời gian để “học ML”**. Random Forest chỉ là một phần tương đối nhỏ. Phần cần nhiều công sức hơn là corpus, normalization, feature definition, annotation, ground truth, leakage prevention và evaluation. RandomForestRegressor bản chất là một ensemble của nhiều regression trees và scikit-learn cung cấp trực tiếp implementation; việc đặt random\_state cố định cũng giúp quá trình fitting tái lập hơn. [*\[1\]*](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestRegressor.html)

Tôi khuyến nghị đặt quy mô benchmark theo ba mức:

| Mức | Base families | Contextual scenarios | Findings mục tiêu | Vai trò |
| :---- | ----: | ----: | ----: | :---- |
| **Minimum defensible** | ≥20 | ≥40 | khoảng ≥150 | Có thể hoàn thành thesis nếu diversity và finding density tốt |
| **Recommended cho bạn** | 24–30 | 48–60 | khoảng 200–300 | Cân bằng annotation, ML và 10 tuần |
| **Stretch theo Protocol v2.3** | 40–60 | 80–120 | ≥300 preferred | Chỉ theo đuổi nếu artifacts có sẵn và annotation tiến triển nhanh |

Mức cuối cùng phải dựa vào execution thực tế, không được chọn theo kết quả của Random Forest. Protocol v2.3 cấm chọn benchmark sau khi nhìn model metrics. fileciteturn0file0

Về dữ liệu, hướng **reuse prior-work artifacts** hiện khả thi hơn nhiều so với tự sinh Terraform mới. IaC-Eval công bố benchmark AWS/Terraform và repository của nó mô tả 458 câu hỏi trong bản đầu; nghiên cứu Security-First Evaluation of Text-to-Terraform năm 2026 công bố artifacts của thí nghiệm AWS Terraform; GenIaC-SecBench báo cáo một corpus lớn gồm 100 scenarios và 1.196 IaC artifacts; đây đều là candidate sources để screening, không phải ground truth prioritization của luận văn. [*\[2\]*](https://github.com/autoiac-project/iac-eval?utm_source=chatgpt.com)

**Đánh giá cuối cùng:** đề tài khả thi trong 10 tuần active với điều kiện bạn thực hiện đúng ba nguyên tắc:

1\.       **Ground truth \+ evaluation quan trọng hơn thêm model.**

2\.       **Random Forest hoàn chỉnh quan trọng hơn Random Forest \+ XGBoost \+ dashboard.**

3\.       **Dừng feature development sau khoảng tuần 8\.**

Ba nguyên tắc này cũng nhất quán với Blueprint v2.1, vốn dành 25% ngân sách cho dataset/ground truth, 20% cho ML và 20% cho experiments/statistics, đồng thời yêu cầu code freeze trước giai đoạn báo cáo và bảo vệ. fileciteturn0file2

## **Cơ sở kế hoạch, giả định và phạm vi phải khóa**

Kế hoạch dưới đây giả định bắt đầu vào **thứ Hai, 28/09/2026**, tức ngay sau ngày hiện tại 26/09/2026. Mười tuần active kết thúc ngày **06/12/2026**; hai tuần từ **07/12 đến 20/12/2026** được giữ làm buffer. Đây là lịch planning, không phải deadline chính thức của trường.

Các quyết định scope đã có cơ sở khá vững: AWS only, Terraform only, Checkov, static analysis, không deploy thật lên AWS, không runtime LLM, Random Forest bắt buộc và XGBoost optional. fileciteturn0file1

**Các giả định và quyết định còn mở** cần được ghi lại ngay từ đầu:

| Hạng mục | Giả định / trạng thái đề xuất | Deadline phải khóa |
| :---- | :---- | :---- |
| Người thực hiện | 1 sinh viên | Đã khóa |
| Kiến thức ML | Beginner; chỉ học phần cần cho supervised regression/ranking | Tuần 1 |
| Active workload | Trung bình \~32–33 giờ/tuần | Theo dõi hàng tuần |
| Buffer | 2 tuần, không dùng để thêm feature | Đã khóa |
| Cloud | AWS only | Đã khóa |
| IaC | Terraform only | Đã khóa |
| Scanner | Checkov 3.3.17 theo Workflow v2.3 | Đã khóa |
| Runtime LLM | Không | Đã khóa |
| Primary ML | Random Forest Regressor | Đã khóa |
| XGBoost | Optional | Chỉ quyết định sau tuần 7 |
| Annotator | A1 \= chính bạn | Đã khóa |
| A2/expert | Có thì review subset; không dependency | Tuần 4 |
| Benchmark size | Recommended 24–30 families / 48–60 scenarios | Freeze tuần 4 |
| Severity mapping | Chưa final | Freeze trước baseline |
| Context scoring formula | Chưa final | Freeze trước ML result |
| Exact RF training target | Chưa final | Freeze trước main training |
| check\_id as feature | Main run nên loại hoặc kiểm soát bằng ablation | Freeze tuần 5 |
| Split strategy | Group theo family\_id | Đã khóa về nguyên tắc |
| Main CV detail | 5-fold GroupKFold nếu đủ families | Freeze tuần 5 |
| NDCG eligibility | ≥3 findings cho @3, ≥5 findings cho @5 | Freeze trước evaluation |
| Gate thresholds | Operational policy, không phải ground truth | Tuần 8 |

Việc split theo family\_id là không thương lượng. Scikit-learn mô tả GroupKFold là K-fold với các group không chồng lấn và mỗi group chỉ xuất hiện một lần trong test set qua các folds; điều này phù hợp trực tiếp với yêu cầu tránh Context A của một Terraform family lọt vào train trong khi Context B xuất hiện ở test. [*\[3\]*](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GroupKFold.html) Protocol v2.3 cũng yêu cầu family-level split và đề xuất GroupKFold hoặc Leave-One-Family-Out. fileciteturn0file0

**Deliverable priority** nên được khóa như sau:

| Cấp | Deliverable |
| :---- | :---- |
| **MUST** | Corpus inventory; provenance/license log; Terraform validation; raw Checkov outputs; normalized findings; finding-level context features; annotation rubric; human ranking; frozen benchmark; family split; severity baseline; contextual baseline; Random Forest; NDCG@3; NDCG@5; Spearman; basic statistical analysis; clean reproduction; thesis; CLI/JSON Gate |
| **SHOULD** | B2 contrastive analysis; permutation importance; minimal ablation; self-retest annotation; expert/A2 review subset nếu có; GitHub Actions |
| **OPTIONAL** | XGBoost; corpus expansion sau mức recommended; additional visualizations; PR comment integration |
| **KHÔNG LÀM** | Runtime GPT/Gemini/Claude; RAG; MCP; multi-agent; Kubernetes; multi-cloud; real AWS deployment; attack graph; SIEM; autonomous remediation; complex dashboard; deep learning |

Protocol và Workflow v2.3 đã loại phần lớn các mục ở dòng cuối để tránh scope creep. fileciteturn0file0 fileciteturn0file1

## **Lịch trình mười tuần, milestones và critical path**

Kế hoạch sau sử dụng khoảng **326 giờ active**. Con số này là planning estimate của tôi, không phải yêu cầu học thuật. Nếu bạn chỉ có khoảng 25 giờ/tuần, phải giảm benchmark hoặc bỏ các SHOULD items, không được lấy giờ từ buffer để giữ nguyên scope.

| Tuần | Ngày | Công việc cụ thể và giờ ước tính | Output bắt buộc | Go/No-Go checkpoint |
| :---- | :---- | :---- | :---- | :---- |
| **W1** | 28/09–04/10 | Freeze protocol **5h**; setup environment **5h**; ML fundamentals cần thiết **8h**; khảo sát/acquire source corpus **8h**; repo/config skeleton **4h** \= **30h** | Protocol freeze, environment chạy được, inventory nguồn v0 | Không code ML trước khi feature/target definition rõ |
| **W2** | 05/10–11/10 | Acquire artifacts **8h**; provenance/license screening **6h**; batch Terraform validate \+ Checkov **12h**; corpus report **8h** \= **34h** | Research corpus inventory, raw scan outputs | Có đủ candidate families và đủ findings để tiếp tục |
| **W3** | 12/10–18/10 | Finding normalizer **10h**; severity mapping **4h**; feature schema/extractor **14h**; unit/QA tests **8h** \= **36h** | normalized\_findings.csv, finding\_context\_features.csv | Feature extraction deterministic và test được |
| **W4** | 19/10–25/10 | Benchmark selection **8h**; Context A/B metadata **8h**; annotation rubric/template **8h**; annotation calibration **6h**; revise/freeze **6h** \= **36h** | Prioritization benchmark v1 \+ frozen rubric | Chỉ freeze benchmark nếu finding density đủ |
| **W5** | 26/10–01/11 | Main annotation **24h**; annotation QA **5h**; ground-truth checks **4h**; family split **5h** \= **38h** | Ground truth v1, frozen train/CV groups | Không chỉnh rank sau khi nhìn model outputs |
| **W6** | 02/11–08/11 | Severity baseline **5h**; context baseline **8h**; preprocessing/target freeze **5h**; RF implementation **10h**; tests **4h** \= **32h** | Baselines \+ RF pipeline chạy end-to-end | RF chạy nhưng chưa cần “thắng” |
| **W7** | 09/11–15/11 | GroupKFold/OoF runs **8h**; B1 evaluation **8h**; NDCG/Spearman **6h**; error analysis **5h**; result checkpoint **5h** \= **32h** | Main experiment results | Đây là scientific core; nếu xong thì thesis đã có research result |
| **W8** | 16/11–22/11 | Wilcoxon/CI/effect **8h**; B2 contrastive **6h**; importance/ablation **6h**; Gate CLI **7h**; docs **3h** \= **30h** | Statistical package \+ lightweight prototype | **STOP FEATURE DEVELOPMENT** |
| **W9** | 23/11–29/11 | Clean reproduction **8h**; final rerun **7h**; tables/figures **6h**; Results/Discussion writing **9h** \= **30h** | Frozen result package | Không thay methodology vì result xấu |
| **W10** | 30/11–06/12 | Integrate thesis **10h**; demo **6h**; slides **5h**; defense Q\&A **4h**; archive/checklist **3h** \= **28h** | Submission/defense-ready package | Thesis phải defendable ngay cuối tuần |
| **Buffer A** | 07/12–13/12 | Chỉ sửa bug, feedback GVHD, formatting, reproduction failures | Stable revision | Không XGBoost mới |
| **Buffer B** | 14/12–20/12 | Submission issues, slide rehearsal, demo fallback, defense prep | Final fallback | Không mở research scope |

Blueprint v2.1 vốn đề xuất khoảng 7–8 tuần research \+ implementation, sau đó ngừng phát triển feature và dành thời gian cho report, testing, bug fixes, demo và defense. Kế hoạch trên kéo active phase thành 10 tuần nhưng vẫn giữ nguyên triết lý code/research freeze trước buffer. fileciteturn0file2

| ![Rendered Mermaid diagram 1][image1] |
| :---: |

**Milestones và acceptance gate:**

| Milestone | Khi nào | Điều kiện đạt |
| :---- | :---- | :---- |
| **Research Freeze** | Cuối W1 | RQ, scope, feature families, evaluation protocol và out-of-scope được ghi version |
| **Corpus Ready** | Cuối W2 | Provenance inventory \+ validation \+ raw Checkov outputs có thể trace |
| **Feature Layer Ready** | Cuối W3 | Một finding có thể đi từ raw JSON → normalized row → context features |
| **Benchmark Freeze** | Cuối W4 | Selection rule, context metadata, rubric, NDCG eligibility không còn thay đổi tùy metric |
| **Ground Truth Freeze** | Cuối W5 | Mọi in-scope finding có unique rank \+ rationale; family\_id QA pass |
| **Scientific MVP** | Cuối W7 | Severity, Context Rule, RF đều có rankings \+ NDCG/Spearman |
| **Experiment Freeze** | Cuối W8 | Statistics/B2 đủ dùng, không thêm feature/model mới |
| **Reproduction Freeze** | Cuối W9 | Clean environment rerun tạo lại bảng chính |
| **Defense Ready** | Cuối W10 | Thesis, slides, demo, README và fallback demo hoàn chỉnh |

Critical path thực tế:

| ![Rendered Mermaid diagram 2][image2] |
| :---: |

Lưu ý **XGBoost không nằm trên critical path**. Nếu W7 chưa có main RF result đáng tin, XGBoost tự động bị loại.

## **Thiết kế dataset, annotation và experiment thực tế**

Protocol v2.3 đề xuất ba tầng Source Corpus → Research Corpus → Prioritization Benchmark, cho phép corpus lớn nhưng chỉ annotate một subset có finding density và diversity đủ tốt. Cách tổ chức này đặc biệt phù hợp với một người vì annotation là bottleneck. fileciteturn0file0

**Kế hoạch annotation nên dùng single-annotator một cách minh bạch:**

| Thành phần | Thiết kế đề xuất |
| :---- | :---- |
| Primary annotator | A1 \= chính bạn |
| Unit được rank | Một security finding trong một scenario |
| Grouping | Scenario |
| Ranking | Unique Rank 1..N, không ties |
| Evidence được xem | check\_name, resource, Terraform source khi cần, objective finding features, business context |
| Evidence không được xem | Severity-baseline ranking, context-baseline output, RF/XGBoost prediction, NDCG/Spearman, feature importance |
| Rationale | 1–3 câu/finding hoặc comparative rationale đủ để audit quyết định |
| Relevance | Tự động: Rank 1→3, Rank 2→2, Rank 3→1, Rank 4+→0 |
| Self-retest | 10–20% scenarios sau khoảng 5–7 ngày, không xem rank cũ |
| A2 | Nếu GVHD/security practitioner có thời gian, review 10–20% subset độc lập |
| Agreement claim | Không gọi A1 self-retest là inter-annotator agreement |
| Ground-truth freeze | Trước khi xem final RF/main experiment output |

Protocol v2.3 cho phép single-annotator khi không có A2, miễn là limitation được công bố; self-retest có thể dùng để kiểm tra consistency nhưng không được gọi là independent annotation. fileciteturn0file0

**Rubric không nên là một công thức số.** Annotator nên sử dụng một sequence reasoning cố định:

Finding là gì?  
 	↓  
 Có Internet exposure / reachability không?  
 	↓  
 Có privilege consequence không?  
 	↓  
 Resource đang ở dev hay production?  
 	↓  
 Asset có critical không?  
 	↓  
 Data có sensitive không?  
 	↓  
 Có compensating / missing controls liên quan không?  
 	↓  
 Nếu chỉ sửa được một finding trước, finding nào tạo giảm rủi ro lớn nhất?

Bạn không nên viết:

Production  	\+3  
 Sensitive   	\+3  
 Public      	\+3  
 Privilege   	\+3

rồi dùng tổng điểm đó trực tiếp làm human ground truth. Làm như vậy khiến RF chỉ học lại deterministic formula và làm yếu construct validity. Protocol/Blueprint đã xác định đây là circularity risk. fileciteturn0file0 fileciteturn0file2

**Sample-size decision rule thực tế:**

| Checkpoint | Rule |
| :---- | :---- |
| Sau screening W2 | Nếu \<20 usable families → mở thêm prior-work sources trước khi annotation |
| Benchmark recommended | 24–30 families, 48–60 contexts |
| Findings | Ưu tiên khoảng 200–300 hơn là cố đạt một raw count cố định |
| NDCG@3 | Scenario phải có ≥3 in-scope findings |
| NDCG@5 | Scenario phải có ≥5 in-scope findings |
| NDCG@5 planning target | Cố có ít nhất khoảng 15–20+ eligible scenarios |
| Annotation throughput | Nếu sau 10 scenarios tốc độ \<2 scenarios/giờ, giảm benchmark thay vì ăn buffer |
| Stretch | Chỉ mở lên 40–60 families khi W4 vẫn đi trước lịch |

Blueprint v2.1 từng đặt mục tiêu thực nghiệm khoảng 15–20 valid paired scenarios nếu dataset cho phép, trong khi v2.3 chuyển 40–60 families / 80–120 scenarios / ≥300 findings thành planning target chứ không phải hard requirement. fileciteturn0file2 fileciteturn0file0

**Experiment matrix:**

| Experiment | Dataset | Methods | Split | Primary output | Vai trò |
| :---- | :---- | :---- | :---- | :---- | :---- |
| **RQ1 Corpus Characterization** | Research Corpus | Không ML | N/A | Finding/category/resource distributions | Mô tả corpus |
| **B1 Context Effect** | Prioritization Benchmark | Severity vs Context Rule | Cùng scenarios | NDCG@3, NDCG@5, Spearman | Trả lời RQ2 |
| **B1 ML Contribution** | Prioritization Benchmark | Context Rule vs RF | Group by family | NDCG@3, NDCG@5, Spearman | Trả lời RQ3 |
| **B2 Contrastive** | Matched A/B | Context/RF score difference | Same family | Δscore, CDA, family median Δ | Secondary |
| **Exploratory** | Test/OoF data | RF | Same split | permutation importance, ablation | Giải thích behavior |
| **XGBoost** | Same frozen benchmark | XGB Regressor | Same split | Same metrics | Optional only |

NDCG phù hợp với mục tiêu này vì nó đánh giá ranking, có thể giới hạn ở top k, và scikit-learn định nghĩa ndcg\_score(..., k=...) bằng cách discount thứ hạng rồi chuẩn hóa theo ideal ranking để cho score 0–1. [*\[4\]*](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.ndcg_score.html)

**Split strategy đề xuất:**

·       Nếu có **≥25 families:** 5-fold GroupKFold.

·       Nếu có **16–24 families:** 4-fold GroupKFold.

·       Nếu nhỏ hơn mức đó: cân nhắc Leave-One-Family-Out, nhưng phải ghi rõ sample nhỏ.

·       Tạo **out-of-fold predictions** để mỗi family/scenario chỉ được dự đoán khi family đó không nằm trong training fold.

·       Baselines được đánh giá trên chính các scenarios giống RF để comparison paired.

GroupKFold bảo đảm các group không overlap và mỗi group xuất hiện một lần trong test across folds. [*\[3\]*](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GroupKFold.html)

**Training target là một open decision phải khóa trước main run.** Tôi đề xuất không dùng trực tiếp relevance 3/2/1/0 làm lựa chọn mặc định vì mọi rank từ 4 trở xuống sẽ cùng target 0, làm mất full ordering. Một lựa chọn đơn giản đáng thảo luận với GVHD là normalized inverse rank:

![][image3]

với N là số findings trong scenario. Khi đó Rank 1 luôn bằng 1, rank cuối bằng 0 và các rank giữa vẫn giữ ordering. Đây là **đề xuất methodology của kế hoạch này**, chưa phải quyết định đã freeze trong Protocol v2.3; nếu GVHD muốn dùng human\_rank, relevance\_grade hoặc target khác thì phải khóa trước W6 và không thay sau khi nhìn result.

Random Forest nên bắt đầu từ configuration đơn giản thay vì hyperparameter search lớn. Scikit-learn hiện mô tả RandomForestRegressor với mặc định 100 trees và cho phép khóa randomness qua random\_state; với luận văn này mục tiêu là đánh giá contribution, không phải chạy leaderboard optimization. [*\[1\]*](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestRegressor.html)

Ví dụ config:

\# configs/experiment\_rf.yaml

 experiment\_id: "B1\_RF\_V1"  
 random\_seed: 42

 split:  
   strategy: "group\_kfold"  
   group\_column: "family\_id"  
   n\_splits: 5

 features:  
   include\_check\_id: false

 model:  
   name: "RandomForestRegressor"  
   n\_estimators: 100  
   random\_state: 42  
   n\_jobs: \-1

 training:  
   target: "FREEZE\_BEFORE\_MAIN\_RUN"

 evaluation:  
   primary:  
 	\- ndcg\_at\_3  
 	\- ndcg\_at\_5  
   secondary:  
 	\- spearman  
   diagnostic:  
 	\- mae  
 	\- rmse

**Statistical analysis** nên sử dụng one metric value per scenario và paired comparisons Severity vs Context và Context vs RF. Wilcoxon signed-rank được SciPy định nghĩa cho hai related paired samples; SciPy cũng lưu ý zeros/ties ảnh hưởng cách tính exact p-value, vì vậy không nên chỉ báo một p-value mà không kiểm tra cấu trúc paired differences. [*\[5\]*](https://docs.scipy.org/doc/scipy-1.12.0/reference/generated/scipy.stats.wilcoxon.html?utm_source=chatgpt.com) Protocol của bạn yêu cầu đi cùng effect size và bootstrap 95% CI. fileciteturn0file0 SciPy cung cấp bootstrap confidence intervals và hỗ trợ paired statistics, nhưng với B2 có clustering theo family thì việc resampling nên được thực hiện ở **family level** thay vì coi từng finding là độc lập. [*\[6\]*](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html?utm_source=chatgpt.com)

Kết quả hợp lệ bao gồm cả:

RF \> Context \> Severity

hoặc:

Context \> Severity  
 RF ≈ Context

hoặc thậm chí:

Severity ≈ Context ≈ RF

Protocol v2.3 đã quy định rõ negative result được chấp nhận và không được thay dataset/annotation để làm hypothesis được hỗ trợ. fileciteturn0file0

## **Implementation, tài nguyên và reproducibility**

Phần implementation nên cực kỳ “boring”: Python modules, CSV/JSON/YAML, command line, không database và không web frontend.

**Resource list:**

| Nhóm | Resource | Khuyến nghị |
| :---- | :---- | :---- |
| OS | Linux / WSL2 / macOS | Chọn một môi trường chính và ghi version |
| IaC | Terraform CLI | Pin một exact version sau corpus smoke test |
| Scanner | Checkov **3.3.17** | Giữ đúng Workflow v2.3 |
| Python | Python **3.11** | Conservative common version cho ML \+ Checkov |
| ML | scikit-learn | Pin exact tested version; 1.9.1 là release hiện hành tại thời điểm nghiên cứu |
| Data | pandas, NumPy | Tabular data |
| Statistics | SciPy | Spearman/Wilcoxon/bootstrap |
| Serialization | joblib | RF/preprocessor artifacts |
| Config | PyYAML | YAML experiment config |
| Plotting | matplotlib | Figures thesis |
| Tests | pytest | Normalization, leakage, metrics |
| Optional ML | XGBoost | Cài chỉ nếu W7 GO |
| VCS | Git | Commit protocol/data/code changes |
| CI | GitHub Actions | SHOULD, không critical |
| Compute | Laptop CPU, \~16 GB RAM reasonable | Không cần GPU cho core RF pipeline |
| Storage | Local \+ Git/LFS/external archive nếu cần | Giữ raw scans/dataset artifacts |

Checkov 3.3.17 theo PyPI yêu cầu Python ≥3.9; scikit-learn 1.9.1 hiện yêu cầu Python ≥3.11, nên Python 3.11 là một lựa chọn chung hợp lý cho môi trường hiện tại. [*\[7\]*](https://pypi.org/project/checkov/3.3.17/?utm_source=chatgpt.com) Việc giữ Checkov 3.3.17 là quyết định reproducibility của Workflow, không phải vì nó bắt buộc phải là phiên bản mới nhất. fileciteturn0file1

**Candidate dataset/resource sources:**

| Source | Vai trò khả dĩ | Cách sử dụng |
| :---- | :---- | :---- |
| Security-First Evaluation of Text-to-Terraform | GenAI-generated AWS Terraform artifacts | Candidate source corpus; giữ provenance |
| GenIaC-SecBench | GenAI IaC corpus lớn | Candidate source để tăng diversity |
| IaC-Eval | AWS/Terraform tasks/dataset | Candidate source/task material, kiểm tra artifact suitability |
| IaCSecBench | Security-oriented Terraform examples | Supplementary/controlled coverage nếu cần, không gọi là GenAI artifact nếu không phải GenAI |
| Pilot hiện tại | Pipeline evidence | Không mặc định trở thành final benchmark |

Security-First Evaluation năm 2026 mô tả 17 AWS Terraform scenarios và công bố artifacts; GenIaC-SecBench báo cáo 100 deployment scenarios và hơn một nghìn IaC artifacts; IaC-Eval repository công bố AWS/Terraform benchmark và license MIT. [*\[8\]*](https://arxiv.org/abs/2608.02672?utm_source=chatgpt.com) Mỗi nguồn vẫn phải qua provenance/license screening của chính thesis trước khi đưa vào final corpus, đúng yêu cầu của Protocol v2.3. fileciteturn0file0

**Repository structure tối thiểu:**

project/  
 ├── configs/  
 │   ├── experiment\_rf.yaml  
 │   ├── features.yaml  
 │   ├── severity\_mapping.yaml  
 │   ├── context\_baseline.yaml  
 │   └── gate\_policy.yaml  
 │  
 ├── data/  
 │   ├── source/  
 │   ├── scenarios/  
 │   ├── raw\_scans/  
 │   ├── normalized/  
 │   ├── features/  
 │   ├── annotations/  
 │   ├── frozen/  
 │   └── splits/  
 │  
 ├── src/  
 │   ├── validation/  
 │   ├── scanner/  
 │   ├── normalization/  
 │   ├── context/  
 │   ├── features/  
 │   ├── dataset/  
 │   ├── baselines/  
 │   ├── models/  
 │   ├── evaluation/  
 │   └── gate/  
 │  
 ├── scripts/  
 │   ├── scan\_all.py  
 │   ├── build\_dataset.py  
 │   ├── train.py  
 │   ├── evaluate.py  
 │   └── run\_gate.py  
 │  
 ├── artifacts/  
 │   ├── models/  
 │   ├── predictions/  
 │   ├── metrics/  
 │   └── figures/  
 │  
 ├── tests/  
 ├── docs/  
 ├── requirements.txt  
 ├── requirements-lock.txt  
 └── README.md

**Implementation checklist:**

| Component | MUST? | Test/acceptance |
| :---- | :---- | :---- |
| Corpus inventory loader | Yes | Mọi artifact có source\_id, family\_id, provenance |
| Terraform validator | Yes | PASS/FAIL \+ logs được lưu |
| Checkov runner | Yes | Raw JSON lưu nguyên vẹn |
| Finding normalizer | Yes | Fixture JSON → expected normalized records |
| Severity mapper | Yes | Mapping versioned; unknown xử lý rõ |
| Scenario context loader | Yes | Không suy từ resource name |
| Infrastructure feature extractor | Yes | Known Terraform fixture → expected features |
| Dataset builder | Yes | Không duplicate key; target không lọt vào feature |
| Leakage validator | Yes | train\_groups ∩ test\_groups \== ∅ |
| Severity baseline | Yes | Stable deterministic ranking |
| Context baseline | Yes | Config frozen, deterministic |
| RF model | Yes | Fit/predict/save/load |
| NDCG implementation | Yes | Test với known perfect/reversed ranking |
| Spearman | Yes | Scenario-level |
| Wilcoxon/statistics | Yes | Paired arrays đúng scenario order |
| B2 analyzer | Should | Match by check\_id \+ normalized address |
| Permutation importance | Should | Chỉ chạy trên fitted model/held-out data |
| Gate CLI | Yes | JSON \+ human-readable result |
| GitHub Actions | Should | Chỉ sau core result |
| XGBoost | Optional | Cùng frozen data/split/metrics |

Scikit-learn cung cấp trực tiếp NDCG và permutation importance. Permutation importance đo mức giảm score khi hoán vị một feature column so với baseline metric và có thể khóa random\_state để reproducible. [*\[9\]*](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.ndcg_score.html)

**Commands gợi ý cho pipeline:**

Terraform validation nên được chạy sau init. HashiCorp ghi rõ terraform validate kiểm tra syntax/internal consistency nhưng không xác thực remote services; terraform init \-backend=false có thể dùng để initialize cho validation mà không truy cập configured backend. [*\[10\]*](https://developer.hashicorp.com/terraform/cli/commands/validate?utm_source=chatgpt.com)

\# Trong từng Terraform artifact directory  
 terraform init \-backend=false \-input=false

 terraform validate \-json \\  
   \> ../../artifacts/validation/scenario\_001.json

Điều này phù hợp với scope **không deploy AWS thật**: validate không phải chứng minh infrastructure có thể deploy hoặc an toàn; nó chỉ là technical admission gate. [*\[11\]*](https://developer.hashicorp.com/terraform/cli/commands/validate?utm_source=chatgpt.com)

Checkov hỗ trợ directory scan, framework filter terraform và JSON output. [*\[12\]*](https://www.checkov.io/2.Basics/CLI%20Command%20Reference.html)

checkov \\  
   \-d data/scenarios/scenario\_001/terraform \\  
   \--framework terraform \\  
   \-o json \\  
   \> data/raw\_scans/scenario\_001.json

Nếu candidate artifact sử dụng external Terraform modules, Checkov có tùy chọn download external modules; tuy nhiên để thesis reproducible và nhanh, nên ưu tiên self-contained artifacts và chỉ bật external download khi nguồn được pin rõ. [*\[13\]*](https://www.checkov.io/7.Scan%20Examples/Terraform.html?utm_source=chatgpt.com)

Pipeline Python có thể thống nhất:

python \-m scripts.build\_dataset \\  
   \--config configs/features.yaml

 python \-m scripts.train \\  
   \--config configs/experiment\_rf.yaml

 python \-m scripts.evaluate \\  
   \--config configs/experiment\_rf.yaml

 python \-m scripts.run\_gate \\  
   \--scenario data/scenarios/demo\_prod \\  
   \--model artifacts/models/rf\_model.joblib \\  
   \--config configs/gate\_policy.yaml

**Reproducibility checklist:**

Terraform version    	→ pin  
 Checkov version      	→ 3.3.17  
 Python version       	→ pin  
 scikit-learn version 	→ pin  
 SciPy version        	→ pin  
 pandas / NumPy       	→ pin  
 random seed          	→ 42 hoặc một số được freeze  
 dataset manifest hash	→ lưu  
 feature schema version   → lưu  
 annotation version   	→ lưu  
 severity mapping version → lưu  
 split file           	→ lưu  
 model parameters     	→ lưu  
 predictions          	→ lưu  
 statistics           	→ lưu

Random Forest có stochastic behavior và scikit-learn khuyến nghị đặt integer random\_state để có deterministic fitting behavior. [*\[14\]*](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestRegressor.html) Workflow v2.3 cũng yêu cầu lưu package versions, scanner version, seed, dataset version, model parameters và outputs trong reproduction run. fileciteturn0file1

Tốt nhất không tạo split lại mỗi lần chạy. Sau khi freeze:

data/splits/family\_folds\_v1.csv

nên chứa:

family\_id,fold\_id  
 family\_001,0  
 family\_002,3  
 family\_003,1  
 ...

Như vậy thesis result không thể thay đổi chỉ vì một lần chạy mới tạo random split khác.

## **Rủi ro, contingency và kill criteria**

Bài toán khó nhất của project này không phải tài nguyên tính toán mà là **methodology failure**. Risk register nên được quản lý hàng tuần như một artifact thật, ví dụ docs/risk\_register.md.

| Risk | Xác suất | Tác động | Early warning | Mitigation | Fallback |
| :---- | :---- | :---- | :---- | :---- | :---- |
| Source artifact/license khó dùng | M | H | Nhiều artifact không có provenance rõ | Screen ngay W1–W2 | Dùng nguồn khác đã freeze |
| Corpus quá sparse | H | H | Phần lớn scenario chỉ 1–3 findings | Ưu tiên ≥3/≥5 findings khi selection | Giảm NDCG@5 claim; mở thêm corpus |
| Annotation quá chậm | H | H | \<2 scenarios/giờ sau calibration | Giảm benchmark trước khi W5 bắt đầu | Minimum 20 families |
| Ground truth quá subjective | H | H | Rationale không ổn định/self-retest lệch nhiều | Rubric \+ blinded retest | Giảm strength của claims |
| Feature extractor sai | M | H | Manual audit không khớp | Fixture/unit tests trước annotation | Manual feature QA subset |
| Checkov severity thiếu | H | M | severity=None | Frozen severity mapping | Report study-defined mapping |
| Family leakage | M | Critical | Same family trong \>1 fold | Automated leakage assertion | Không chạy experiment đến khi fix |
| check\_id memorization | M | H | Feature importance bị identifier chi phối | Main run exclude check\_id; ablation | Report sensitivity |
| Ground truth–feature circularity | H | Critical | Annotation trở thành weighted formula | Human comparative rationale, baseline riêng | Giảm claim thành rubric-learning |
| RF không hơn context rule | H | Low | NDCG tương đương/thấp hơn | Không “fix” result | **Accept negative result** |
| Sample quá nhỏ cho statistics | M | H | \<15–20 valid scenarios | Paired metrics \+ bootstrap \+ transparent limitation | Không overclaim significance |
| Tool/package drift | M | M | Clean rerun khác result | Pin versions \+ raw artifacts | Recreate from lock file |
| Gate prototype trễ | M | Low | W8 chưa có CLI | Giảm Gate thành JSON/CLI | Research vẫn hoàn chỉnh |
| Thesis writing trễ | H | H | W8 chưa có Methods draft | Viết Methods song song từ W3 | Bỏ optional analysis |
| Scope creep | H | Critical | “Thêm XGBoost/dashboard/RAG cho đẹp” | MUST/SHOULD/OPTIONAL firewall | Tự động reject ngoài critical path |

Pilot hiện tại đã chứng minh technical pipeline khả thi: 10/10 validation, 10/10 parsing, 118 raw failed findings, coverage 8/8 categories và contrastive pair verification pass. Điều này làm giảm rủi ro “Terraform → Checkov → normalization không chạy được”, nhưng **không làm giảm rủi ro ground truth, corpus density và data leakage**. fileciteturn0file1

**Kill / pivot criteria nên được định nghĩa trước:**

| Trigger | Quyết định |
| :---- | :---- |
| W2 không có ≥20 usable families | Mở thêm prior-work source; không bắt đầu annotation |
| Đa số scenario \<3 findings | Thay selection strategy; không ép NDCG |
| NDCG@5-eligible scenarios quá ít | NDCG@3 vẫn primary; NDCG@5 report trên eligible subset và ghi limitation |
| Feature extraction không ổn cuối W3 | Giảm optional feature set về internet\_exposure, privilege\_impact, reachability |
| Annotation throughput quá thấp | Cap benchmark ở minimum defensible size |
| A2 không có | Tiếp tục single-annotator \+ self-retest; công bố limitation |
| RF không hơn contextual rule | Không chỉnh dataset; kết luận negative result |
| RF pipeline chưa ổn cuối W7 | **Kill XGBoost** |
| B2 chiếm quá nhiều thời gian | Giảm B2 xuống descriptive subset |
| Gate chưa xong cuối W8 | CLI/JSON tối thiểu, không GitHub Actions |
| W8 kết thúc | **No new model, feature, dataset source, dashboard** |
| Clean reproduction fail W9 | Dừng viết figure mới cho đến khi fix |
| Buffer bắt đầu | Chỉ bug/review/format/demo; không research expansion |

Negative-result policy là đặc biệt quan trọng: v2.3 yêu cầu không chỉnh annotation, data hay protocol để làm hypothesis được hỗ trợ. fileciteturn0file0

Một contingency quan trọng khác: scanner failure không được hiểu là “no findings \= secure”. Protocol yêu cầu Checkov failure không tự động PASS và ML failure có thể fallback sang deterministic/severity policy ở prototype layer. fileciteturn0file0

## **Acceptance criteria cho luận văn và bảo vệ**

Luận văn không nên được đánh giá bằng câu hỏi **“RF có thắng không?”**, mà bằng câu hỏi **“nghiên cứu có trả lời được RQ một cách reproducible và defendable không?”**

Tôi đề xuất acceptance checklist cuối cùng:

| Khu vực | Acceptance criterion |
| :---- | :---- |
| **Research framing** | RQ1/RQ2/RQ3 nhất quán từ proposal đến Results |
| **Scope discipline** | AWS \+ Terraform \+ Checkov; không runtime LLM; không real deployment |
| **Corpus** | Có inventory, provenance và exclusion reason |
| **Benchmark** | Selection rule được freeze trước model result |
| **Data model** | source\_id, family\_id, scenario\_id, finding\_id trace được |
| **Features** | Finding-level features tạo trước annotation |
| **Context** | Business context từ explicit metadata, không từ naming guess |
| **Ground truth** | Tất cả in-scope findings có rank và rationale |
| **Single annotator** | Limitation ghi rõ; self-retest không gọi là IAA |
| **Leakage** | Automated proof rằng train/test families không overlap |
| **Baseline A** | Severity-only chạy reproducibly |
| **Baseline B** | Contextual deterministic scoring được freeze |
| **ML** | Random Forest fit/predict/save/load được |
| **XGBoost** | Không bắt buộc |
| **Main metrics** | NDCG@3, NDCG@5 có eligibility reporting |
| **Secondary** | Spearman report đúng vai trò |
| **Statistics** | Paired comparison \+ sample size \+ CI/effect interpretation |
| **Negative result** | Có thể giải thích mà không sửa methodology |
| **Validity** | Construct/internal/external/conclusion threats được thảo luận |
| **Reproducibility** | Clean rerun từ frozen artifacts/config tạo lại main results |
| **Prototype** | Terraform → Checkov → Context → Score → Rank → Gate |
| **Demo** | Chạy được 5–8 phút hoặc có recorded/frozen fallback |
| **Thesis artifacts** | Tables/figures trace đến experiment IDs |
| **README** | Người khác biết setup, reproduce, run demo |
| **Defense** | Trả lời được “AI ở đâu?”, “tại sao cần ML?”, “nếu ML không thắng?” |

Đối với defense, bạn phải giải thích được toàn bộ đề tài bằng sơ đồ sau mà không cần đi vào thuật toán Random Forest quá sâu:

AI-generated Terraform  
     	↓  
 Checkov detects findings  
     	↓  
 Context adds deployment/security meaning  
     	↓  
 Humans define study priority  
     	↓  
 Severity / Rule / RF try to reproduce that priority  
     	↓  
 NDCG measures ranking quality  
     	↓  
 Statistics compare approaches  
     	↓  
 Security Gate demonstrates practical use

Câu trả lời chuẩn cho **“AI ở đâu?”**:

Machine Learning là thành phần AI chính của nghiên cứu, cụ thể là Random Forest dùng để học contextual priority từ annotated examples. Generative AI chỉ cung cấp một phần experimental Terraform artifacts; runtime pipeline không phụ thuộc LLM.

Câu trả lời chuẩn cho **“Tại sao không chỉ dùng if/else?”**:

Chính vì deterministic rules có thể đủ tốt nên luận văn đưa chúng thành baseline. Thí nghiệm không giả định ML tốt hơn; RQ3 kiểm tra xem Random Forest có tạo measurable benefit ngoài contextual rule hay không.

Câu trả lời chuẩn cho **“Nếu Random Forest không tốt hơn?”**:

Đây vẫn là một empirical result hợp lệ. Nó cho thấy trong benchmark và context representation được nghiên cứu, độ phức tạp bổ sung của ML chưa tạo lợi ích rõ ràng so với deterministic contextual scoring.

Câu trả lời chuẩn cho **“Ground truth có phải risk thật không?”**:

Không. Ground truth là human-defined contextual security priority theo rubric của nghiên cứu, không phải xác suất compromise ngoài thực tế.

Câu trả lời chuẩn cho **“Tại sao không deploy AWS thật?”**:

Research question tập trung vào static IaC finding prioritization. Terraform validate kiểm tra configuration syntax/internal consistency nhưng không xác minh remote infrastructure, và thesis cố ý không mở rộng sang runtime/deployment risk để giữ scope có thể thực hiện. [*\[11\]*](https://developer.hashicorp.com/terraform/cli/commands/validate?utm_source=chatgpt.com)

**Definition of Done cuối cùng** nên là:

\[PASS\] Scope frozen  
 \[PASS\] Corpus archived  
 \[PASS\] Provenance documented  
 \[PASS\] Checkov raw outputs retained  
 \[PASS\] Normalized findings frozen  
 \[PASS\] Feature schema frozen  
 \[PASS\] Annotation rubric frozen  
 \[PASS\] Ground truth frozen  
 \[PASS\] Family leakage test passed  
 \[PASS\] Severity baseline completed  
 \[PASS\] Context baseline completed  
 \[PASS\] Random Forest completed  
 \[PASS\] NDCG@3 completed  
 \[PASS\] NDCG@5 completed  
 \[PASS\] Spearman completed  
 \[PASS\] Statistical comparison completed  
 \[PASS\] Threats to validity written  
 \[PASS\] Clean reproduction completed  
 \[PASS\] Security Gate CLI/JSON completed  
 \[PASS\] Thesis completed  
 \[PASS\] Slides \+ demo \+ fallback ready

 \[OPTIONAL\] XGBoost  
 \[OPTIONAL\] GitHub Actions  
 \[OPTIONAL\] A2 annotation subset

Kế hoạch này cố ý đặt thesis ở trạng thái **scientifically complete vào cuối W7–W8**, sau đó W9–W10 chỉ củng cố reproduction, report và defense. Với một người chưa có kinh nghiệm ML, đây an toàn hơn rất nhiều so với dành 9–10 tuần để build hệ thống rồi mới bắt đầu evaluation.

Câu chốt để điều khiển toàn bộ project trong ba tháng là:

**Đến cuối tuần 5 phải có dữ liệu đáng tin; đến cuối tuần 7 phải có kết quả khoa học; đến cuối tuần 8 phải dừng mở rộng; hai tuần cuối cùng tuyệt đối không được biến thành thời gian cứu một scope quá lớn.**

---

[*\[1\]* *\[14\]*](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestRegressor.html) RandomForestRegressor — scikit-learn 1.9.0 documentation

[*https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestRegressor.html*](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestRegressor.html)

[*\[2\]*](https://github.com/autoiac-project/iac-eval?utm_source=chatgpt.com) GitHub \- autoiac-project/iac-eval: \[NeurIPS 24\] IaC-Eval: A Code Generation Benchmark for Cloud Infrastructure-as-Code programs · GitHub

[*https://github.com/autoiac-project/iac-eval?utm\_source=chatgpt.com*](https://github.com/autoiac-project/iac-eval?utm_source=chatgpt.com)

[*\[3\]*](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GroupKFold.html) GroupKFold — scikit-learn 1.9.0 documentation

[*https://scikit-learn.org/stable/modules/generated/sklearn.model\_selection.GroupKFold.html*](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GroupKFold.html)

[*\[4\]* *\[9\]*](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.ndcg_score.html) ndcg\_score — scikit-learn 1.9.0 documentation

[*https://scikit-learn.org/stable/modules/generated/sklearn.metrics.ndcg\_score.html*](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.ndcg_score.html)

[*\[5\]*](https://docs.scipy.org/doc/scipy-1.12.0/reference/generated/scipy.stats.wilcoxon.html?utm_source=chatgpt.com) scipy.stats.wilcoxon — SciPy v1.12.0 Manual

[*https://docs.scipy.org/doc/scipy-1.12.0/reference/generated/scipy.stats.wilcoxon.html?utm\_source=chatgpt.com*](https://docs.scipy.org/doc/scipy-1.12.0/reference/generated/scipy.stats.wilcoxon.html?utm_source=chatgpt.com)

[*\[6\]*](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html?utm_source=chatgpt.com) bootstrap — SciPy v1.18.0 Manual

[*https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html?utm\_source=chatgpt.com*](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html?utm_source=chatgpt.com)

[*\[7\]*](https://pypi.org/project/checkov/3.3.17/?utm_source=chatgpt.com) checkov · PyPI

[*https://pypi.org/project/checkov/3.3.17/?utm\_source=chatgpt.com*](https://pypi.org/project/checkov/3.3.17/?utm_source=chatgpt.com)

[*\[8\]*](https://arxiv.org/abs/2608.02672?utm_source=chatgpt.com) Security-First Evaluation of Text-to-Terraform: Benchmarking LLMs and SLMs for Secure IaC Generation

[*https://arxiv.org/abs/2608.02672?utm\_source=chatgpt.com*](https://arxiv.org/abs/2608.02672?utm_source=chatgpt.com)

[*\[10\]* *\[11\]*](https://developer.hashicorp.com/terraform/cli/commands/validate?utm_source=chatgpt.com) terraform validate command reference | Terraform | HashiCorp Developer

[*https://developer.hashicorp.com/terraform/cli/commands/validate?utm\_source=chatgpt.com*](https://developer.hashicorp.com/terraform/cli/commands/validate?utm_source=chatgpt.com)

[*\[12\]*](https://www.checkov.io/2.Basics/CLI%20Command%20Reference.html) CLI Command Reference \- checkov

[*https://www.checkov.io/2.Basics/CLI%20Command%20Reference.html*](https://www.checkov.io/2.Basics/CLI%20Command%20Reference.html)

[*\[13\]*](https://www.checkov.io/7.Scan%20Examples/Terraform.html?utm_source=chatgpt.com) Terraform Scanning \- checkov

[*https://www.checkov.io/7.Scan%20Examples/Terraform.html?utm\_source=chatgpt.com*](https://www.checkov.io/7.Scan%20Examples/Terraform.html?utm_source=chatgpt.com)

# Project Execution Phases

# **Project Execution Phases — Các giai đoạn triển khai đề tài**

## **1\. Tổng thể**

Đề tài nên được triển khai theo chuỗi:

**PHASE 0 — Design Freeze**  
↓  
**PHASE 1 — Dataset / Corpus Preparation**  
↓  
**PHASE 2 — Terraform & Checkov Pipeline**  
↓  
**PHASE 3 — Context & Feature Engineering**  
↓  
**PHASE 4 — Ground Truth & Benchmark Construction**  
↓  
**PHASE 5 — Baseline Experiments**  
↓  
**PHASE 6 — Random Forest ML**  
↓  
**PHASE 7 — Evaluation & Research Analysis**  
↓  
**PHASE 8 — Prototype, Thesis & Defense**

Nguyên tắc quan trọng:

> Không chuyển sang ML cho đến khi Dataset, Feature và Ground Truth đủ ổn định.

---

# **PHASE 0 — DESIGN FREEZE**

**Thời gian:** Tuần 1  
**Mục tiêu:** Chốt thiết kế nghiên cứu trước khi code nhiều.

Đây là phase giúp tránh tình trạng đang làm lại thay đổi dataset, feature, metric hoặc model.

### **Cần chốt**

| Thành phần | Cần quyết định |
| ----- | ----- |
| Research Questions | RQ1, RQ2, RQ3 |
| Cloud | AWS |
| IaC | Terraform |
| Scanner | Checkov 3.3.17 |
| Main ML | Random Forest |
| Baselines | Severity-only \+ Contextual Rule |
| Primary metrics | NDCG@3, NDCG@5 |
| Secondary metric | Spearman |
| Unit of analysis | Security finding trong một scenario |
| Split principle | Theo `family_id`, không random finding |
| Context schema | Business context \+ infrastructure context |
| Annotation principle | Human contextual priority ranking |

Bốn quyết định đặc biệt phải được ghi thành **OPEN → FROZEN** trước main experiment:

**D1. ML Target:** Random Forest thực sự học target `y` nào?

**D2. Severity Mapping:** vì Checkov pilot có thể không cung cấp severity trực tiếp, severity-only baseline sử dụng mapping nào?

**D3. `check_id`:** có được sử dụng làm ML feature hay chỉ dùng cho identification/analysis/ablation?

**D4. Validation Strategy:** fixed grouped train/test, GroupKFold hay Leave-One-Family-Out?

Các tài liệu v2.3 nhấn mạnh việc freeze protocol và không thay đổi thiết kế dựa trên kết quả model sau này.

### **Deliverable**

`research_design_v1.md`

`scope_v1.md`

`feature_spec_draft.md`

`annotation_protocol_draft.md`

`experiment_config_draft.md`

### **Exit Criteria**

**GO khi:** bạn có thể giải thích được:

**Research Question → Dataset → Ground Truth → Experiment → Metric**

mà chưa cần nói về giao diện hay deployment.

---

# **PHASE 1 — DATASET / CORPUS PREPARATION**

**Thời gian:** Tuần 1–2  
**Mục tiêu:** Có Terraform artifacts thật sự dùng được cho nghiên cứu.

Chiến lược v2.3 là ưu tiên **reuse → reproduce → extend**, thay vì tự tạo toàn bộ benchmark từ đầu.

### **Luồng**

Published / Reproducible  
AI-generated Terraform  
        ↓  
Source Corpus  
        ↓  
Filter  
        ↓  
AWS \+ Terraform  
        ↓  
Valid / Processable  
        ↓  
Checkov Scannable  
        ↓  
Research Corpus

Mỗi artifact nên có tối thiểu:

source\_id  
artifact\_id  
family\_id  
terraform\_path  
provenance  
license

Sau đó chạy thống kê:

\# families  
\# Terraform artifacts  
\# Checkov findings  
findings / scenario  
resource types  
security categories

Planning target trong protocol là khoảng **40–60 base families, 80–120 contextual scenarios và ≥300 findings**, nhưng đây là **planning target, không phải hard requirement**. Quan trọng hơn là benchmark sạch, có provenance, đủ finding density, đa dạng và có thể annotation tốt.

### **Deliverable**

data/source/  
data/research\_corpus/

corpus\_manifest.csv  
corpus\_statistics.csv  
dataset\_provenance.md

### **Exit Criteria**

**GO:** đủ corpus để tiếp tục nghiên cứu.

**NO-GO / PIVOT:** nếu corpus quá ít hoặc phần lớn artifact không validate/scan được → mở rộng nguồn dữ liệu trước, chưa làm ML.

---

# **PHASE 2 — TERRAFORM \+ CHECKOV PIPELINE**

**Thời gian:** Tuần 2  
**Mục tiêu:** Biến Terraform thành dataset security findings có cấu trúc.

### **Pipeline**

Terraform  
   ↓  
Terraform Validate  
   ↓  
Checkov 3.3.17  
   ↓  
Raw JSON  
   ↓  
Finding Normalizer  
   ↓  
Normalized Findings

Pipeline này phải chạy được **batch**, không làm thủ công từng file.

Normalized finding có thể có dạng:

finding\_id  
family\_id  
scenario\_id

check\_id  
check\_name

resource\_address  
resource\_type

file\_path  
line\_start  
line\_end

scanner information

Một lưu ý quan trọng của methodology: một Checkov finding là **scanner finding**, không nhất thiết tương ứng với một vulnerability độc lập.

### **Deliverable**

src/validate.py  
src/scan.py  
src/normalize.py

data/checkov\_raw/  
data/normalized/

scan\_summary.csv

### **Exit Criteria**

Cho một Terraform artifact bất kỳ:

Terraform  
→ Validate  
→ Checkov  
→ JSON  
→ Normalized Findings

chạy được end-to-end.

**Chưa cần ML.**

---

# **PHASE 3 — CONTEXT & FEATURE ENGINEERING**

**Thời gian:** Tuần 3  
**Mục tiêu:** Biến finding thành ML-ready data.

Đây là phần cybersecurity quan trọng nhất của đề tài.

### **Scenario / Business Context**

environment  
asset\_criticality  
data\_sensitivity

Ví dụ:

Context A  
environment \= dev  
criticality \= low  
sensitivity \= low

Context B  
environment \= prod  
criticality \= high  
sensitivity \= high

### **Infrastructure / Finding Context**

Candidate features:

internet\_exposure  
privilege\_impact  
reachability

public\_access  
wildcard\_action  
wildcard\_resource  
encryption\_missing  
logging\_missing

Chỉ extract feature khi có **evidence rõ ràng từ Terraform, scanner hoặc explicit metadata**.

Không được suy đoán kiểu:

resource\_name \= "prod-db"

→ chắc chắn criticality \= HIGH

### **Feature pipeline**

Normalized Finding  
        \+  
Scenario Context  
        \+  
Infrastructure Facts  
        ↓  
Feature Builder  
        ↓  
Feature Dataset X

### **FEATURE FREEZE**

Sau khi kiểm tra feature extraction:

FEATURE\_SPEC\_VERSION \= v1.0

Từ thời điểm này không được thêm/bớt feature chỉ vì thấy kết quả ML chưa tốt.

### **Deliverable**

src/context.py  
src/features.py

feature\_spec\_v1.md  
features\_v1.csv  
feature\_validation\_report.md

### **Exit Criteria**

Chọn ngẫu nhiên findings và có thể trả lời:

> “Feature này bằng HIGH/LOW/TRUE/FALSE vì evidence nào trong Terraform/context?”

Nếu không giải thích được → feature chưa đủ đáng tin cậy.

---

# **PHASE 4 — GROUND TRUTH & BENCHMARK**

**Thời gian:** Tuần 4  
**Mục tiêu:** Tạo “đáp án tham chiếu” để model học và để đánh giá ranking.

Đây là phase quan trọng nhất của toàn đề tài.

Pipeline:

Scenario  
   ↓  
Security Findings  
   ↓  
Context  
   ↓  
Human Review  
   ↓  
Priority Ranking

Ví dụ:

Finding A → Rank 1  
Finding C → Rank 2  
Finding B → Rank 3  
Finding D → Rank 4

Evaluation relevance mapping đã được protocol định nghĩa:

Rank 1 → 3  
Rank 2 → 2  
Rank 3 → 1  
Rank 4+ → 0

### **Annotation phải tránh**

Human Rank  
    ↑  
Model Prediction

hoặc:

Human Rank  
    ↑  
Context Baseline Score

Annotator không nên xem model prediction hoặc final experiment result trước khi quyết định ground truth.

### **DATASET FREEZE \+ ANNOTATION FREEZE**

Khi annotation hoàn tất:

benchmark\_v1.csv  
annotation\_v1.csv

Đây trở thành dataset chính thức cho experiment.

### **Deliverable**

annotation\_protocol\_v1.md  
annotation\_v1.csv  
benchmark\_v1.csv  
benchmark\_statistics.md

### **Exit Criteria**

Mỗi scenario trong evaluation set phải có:

findings  
\+  
features  
\+  
context  
\+  
human ranking

**Nếu Ground Truth chưa ổn → không sang ML.**

---

# **PHASE 5 — BASELINE EXPERIMENTS**

**Thời gian:** Tuần 5  
**Mục tiêu:** Có thứ để so sánh với ML.

Đừng train Random Forest đầu tiên.

Thứ tự:

Baseline 1  
Severity-only  
        ↓  
Baseline 2  
Deterministic Contextual Scoring  
        ↓  
Model  
Random Forest

### **Baseline 1 — Severity-only**

Finding  
↓  
Frozen Severity Mapping  
↓  
Priority  
↓  
Ranking

### **Baseline 2 — Contextual Rule**

Ví dụ về mặt khái niệm:

Finding  
\+  
Infrastructure Context  
\+  
Business Context  
↓  
Frozen Deterministic Formula  
↓  
Score  
↓  
Ranking

Công thức/weight thực tế phải được **freeze trước khi xem final ML comparison**.

### **Deliverable**

src/baselines.py

severity\_baseline\_results.csv  
context\_baseline\_results.csv  
baseline\_report.md

### **Exit Criteria**

Bạn đã có:

Human Ranking  
Severity Ranking  
Context Rule Ranking

và tính thử được NDCG.

Nếu đến đây bạn làm được thì **nghiên cứu đã có baseline khoa học**, dù chưa có ML.

---

# **PHASE 6 — RANDOM FOREST ML**

**Thời gian:** Tuần 6  
**Mục tiêu:** Train model ML đầu tiên.

Đây thực tế không phải phase dài nhất.

### **ML pipeline**

Benchmark Dataset  
       ↓  
Group by family\_id  
       ↓  
Train / Validation / Test  
       ↓  
Preprocessing  
       ↓  
RandomForestRegressor  
       ↓  
Priority Score  
       ↓  
Sort  
       ↓  
Predicted Ranking

Nguyên tắc cực kỳ quan trọng:

Family A Context A  
Family A Context B

không được để một cái ở training và một cái ở testing.

Nếu không, model có thể đã thấy gần như cùng Terraform trong training → **data leakage**.

Protocol v2.3 yêu cầu split theo family/scenario family thay vì random finding split.

### **Bạn chỉ cần học ML tới mức này**

Feature X  
Target y  
Train  
Predict  
Overfitting  
Train/Test Split  
Group Split  
Random Forest  
Feature Importance

Không cần học:

Neural Networks  
CNN  
RNN  
Transformer  
LLM training  
Reinforcement Learning

### **Deliverable**

src/train.py  
src/predict.py

models/random\_forest\_v1.pkl

rf\_predictions.csv  
training\_config.json  
training\_report.md

### **Exit Criteria**

Model nhận một feature vector chưa thấy trong training và trả được:

priority\_score

sau đó tạo ranking cho scenario.

---

# **PHASE 7 — EVALUATION & RESEARCH ANALYSIS**

**Thời gian:** Tuần 7  
**Mục tiêu:** Trả lời Research Questions.

Đây mới là nơi quyết định contribution của luận văn.

### **Main comparison**

                Human Ground Truth  
                        ↑  
                        │  
        ┌───────────────┼───────────────┐  
        │               │               │  
Severity Ranking   Context Ranking   RF Ranking

Primary metrics:

NDCG@3  
NDCG@5

Secondary:

Spearman correlation

Diagnostic khi phù hợp:

MAE  
RMSE

Protocol xác định NDCG là metric chính cho ranking, còn regression metrics chủ yếu mang tính diagnostic.

Sau đó mới xem xét:

paired differences  
Wilcoxon  
effect size  
bootstrap confidence interval

nếu số scenario đủ để việc thống kê có ý nghĩa.

### **Kết quả có thể xảy ra**

Severity \< Context Rule \< RF

hoặc:

Severity \< RF ≈ Context Rule

hoặc thậm chí:

Severity \< Context Rule \> RF

Cả ba đều có thể là **kết quả nghiên cứu hợp lệ**.

Không sửa dataset, annotation hoặc methodology để buộc ML thắng. Protocol v2.3 cũng xác định negative result là kết quả có thể chấp nhận.

### **Deliverable**

src/evaluate.py

evaluation\_results.csv  
metric\_summary.csv  
statistical\_analysis.csv

figures/  
tables/

research\_findings.md

### **Exit Criteria**

Bạn có thể trả lời bằng evidence:

**RQ1:** Corpus AI-generated Terraform được đánh giá có những misconfiguration/pattern nào?

**RQ2:** Context-aware prioritization khác/cải thiện như thế nào so với severity-only?

**RQ3:** Random Forest có cung cấp lợi ích đo được so với deterministic contextual scoring hay không?

---

# **PHASE 8 — PROTOTYPE \+ THESIS \+ DEFENSE**

**Thời gian:** Tuần 8  
**Mục tiêu:** Chuyển kết quả nghiên cứu thành demo tối thiểu.

Chỉ làm prototype **sau khi core experiment hoạt động**.

### **Operational pipeline**

New Terraform  
      ↓  
Terraform Validate  
      ↓  
Checkov  
      ↓  
Normalize  
      ↓  
Context  
      ↓  
Feature Builder  
      ↓  
Trained Random Forest  
      ↓  
Priority Scores  
      ↓  
Ranked Findings  
      ↓  
Security Gate

Output tối thiểu:

CLI  
\+  
JSON

Ví dụ về concept:

Security Prioritization Result

1\. CKV\_XXX  
   Priority: HIGH

2\. CKV\_YYY  
   Priority: MEDIUM

3\. CKV\_ZZZ  
   Priority: LOW

Gate: REVIEW

Security Gate chỉ là **operational prototype**, không phải scientific ground truth.

Nếu còn thời gian mới thêm:

GitHub Actions  
feature importance visualization  
contrastive A/B experiment  
XGBoost  
additional data

### **Deliverable**

src/gate.py  
demo/  
example\_output.json

README.md  
reproduction\_guide.md  
final\_results/  
thesis/  
defense/  
---

# **BUFFER — TUẦN 9–10**

Hai tuần cuối không nên dùng để thêm feature.

Dùng để:

fix bugs  
rerun experiments  
verify reproducibility  
check tables/figures  
review thesis  
prepare demo  
prepare slides  
practice defense

Nếu mọi thứ chạy tốt, đây là thời gian polish.

Nếu bị chậm, đây là **recovery buffer**.

---

# **Timeline dễ theo dõi**

| Tuần | Phase | Mục tiêu chính | Output quan trọng |
| ----- | ----- | ----- | ----- |
| 1 | P0 | Design Freeze | Research design |
| 1–2 | P1 | Corpus | Research Corpus |
| 2 | P2 | Terraform \+ Checkov | Normalized findings |
| 3 | P3 | Context \+ Features | Feature Dataset |
| 4 | P4 | Ground Truth | Prioritization Benchmark |
| 5 | P5 | Baselines | Severity \+ Context results |
| 6 | P6 | Random Forest | ML predictions |
| 7 | P7 | Evaluation | Research results |
| 8 | P8 | Prototype | CLI/JSON demo |
| 9 | Buffer | Fix \+ rerun | Reproducible final experiment |
| 10 | Final | Thesis \+ Defense | Thesis \+ slides \+ demo |

---

# **Critical Path**

Phần bắt buộc phải đi theo thứ tự:

Dataset  
   ↓  
Checkov Findings  
   ↓  
Normalization  
   ↓  
Context / Features  
   ↓  
Ground Truth  
   ↓  
Dataset Freeze  
   ↓  
Baselines  
   ↓  
Random Forest  
   ↓  
Evaluation

Đây là **critical path**.

Không nên làm kiểu:

Dashboard ───────────────┐  
GitHub Actions ──────────┤  
XGBoost ─────────────────┤  
Random Forest ───────────┤  
Annotation ──────────────┤  
Dataset expansion ───────┘

tất cả cùng lúc.

Một người làm như vậy rất dễ mất kiểm soát.

---

# **Thứ tự ưu tiên khi thiếu thời gian**

Nếu chậm tiến độ, cắt theo thứ tự:

1\. Visualization đẹp  
        ↓  
2\. Extra dataset expansion  
        ↓  
3\. XGBoost  
        ↓  
4\. Advanced explainability  
        ↓  
5\. GitHub Actions  
        ↓  
6\. Contrastive secondary experiment

Không cắt:

Ground Truth  
Dataset QA  
Baselines  
Random Forest  
Leakage Prevention  
NDCG Evaluation  
Research Analysis  
Threats to Validity  
---

# **Cách quản lý hằng ngày**

Mỗi task chỉ nên ở một trong năm trạng thái:

TODO  
  ↓  
DOING  
  ↓  
VERIFY  
  ↓  
DONE

hoặc:

BLOCKED

Và mỗi phase chỉ được đánh dấu **DONE** khi deliverable của phase tồn tại.

Ví dụ:

PHASE 3 — FEATURE ENGINEERING

\[✓\] Context schema  
\[✓\] Infrastructure feature definitions  
\[✓\] Feature extractor  
\[✓\] Manual verification  
\[✓\] Missing-value handling  
\[✓\] feature\_spec\_v1.md  
\[✓\] features\_v1.csv

STATUS: DONE

Không dùng:

> “Feature Engineering — 80%”

vì rất khó biết 80% thực sự nghĩa là gì.

---

# **5 Freeze Point quan trọng**

Toàn project nên có năm mốc khóa:

DESIGN FREEZE  
      ↓  
DATASET FREEZE  
      ↓  
FEATURE FREEZE  
      ↓  
ANNOTATION FREEZE  
      ↓  
EXPERIMENT FREEZE

Sau **Experiment Freeze**, không thay dataset, feature, annotation rubric, split hoặc baseline chỉ vì kết quả ML không đẹp.

Nếu phải thay đổi vì phát hiện lỗi methodology, phải:

Document reason  
→ bump version  
→ rerun affected experiments  
→ report change  
---

# **Definition of Done**

Đề tài được xem là **DONE** khi pipeline sau chạy hoàn chỉnh:

AI-generated Terraform Corpus  
            ↓  
Terraform Validation  
            ↓  
Checkov  
            ↓  
Normalized Security Findings  
            ↓  
Context \+ Features  
            ↓  
Human Ground Truth  
            ↓  
Prioritization Benchmark  
            ↓  
┌────────────┼─────────────┐  
│            │             │  
Severity   Context        RF  
Baseline   Baseline       Model  
│            │             │  
└────────────┼─────────────┘  
             ↓  
       Ranked Findings  
             ↓  
     NDCG / Spearman  
             ↓  
       RQ Conclusions  
             ↓  
       CLI Security Gate  
             ↓  
 Thesis \+ Results \+ Limitations

**ML không cần phải thắng baseline để project được coi là thành công.**

Điều kiện thành công là bạn có một methodology hợp lý, dataset có kiểm soát, ground truth có giải thích, không leakage, experiment reproducible và đủ evidence để trả lời Research Questions.

---

# **Cách nghĩ đơn giản nhất khi triển khai**

Trong giai đoạn đầu:

> **Đừng nghĩ “tôi phải làm Machine Learning”.**

Hãy nghĩ:

1\. Tôi cần dữ liệu gì?  
↓  
2\. Tôi lấy security findings thế nào?  
↓  
3\. Tôi biểu diễn context thế nào?  
↓  
4\. Ai quyết định finding nào quan trọng hơn?  
↓  
5\. Rule đơn giản làm tốt tới đâu?  
↓  
6\. ML học được gì?  
↓  
7\. ML có thực sự giúp không?  
↓  
8\. Tôi chứng minh điều đó bằng metric nào?

Khi 8 câu này được trả lời bằng artifact và experiment cụ thể, phần lớn luận văn đã hình thành.

Với bạn, **Phase 0–4 mới là phần cần tập trung nhất**, không phải Random Forest. Khi tới Phase 6, việc train Random Forest bằng scikit-learn thực ra chỉ là một phần tương đối nhỏ; dataset, feature, ground truth và chống leakage mới quyết định chất lượng nghiên cứu.

---

# Privilege Impact Contract — Normative Clarification

> [!IMPORTANT]
> This section is normative.
>
> It supersedes earlier descriptions of `privilege_impact` wherever
> those descriptions conflict with this contract.

`privilege_impact` represents the ordinal potential authorization
capability of the Checkov-relevant IAM statement.

It is a contextual observation, not a final risk score and not an
estimate of fully evaluated runtime authorization.

The approved mapping is:

| Value | Meaning |
|---|---|
| `0` | No granted privilege capability; supported primary case is a deterministically identified `Effect = "Deny"` statement |
| `1` | Read, list, describe, query, or equivalent observation capability |
| `2` | Non-authorization administrative mutation or resource/service state-changing capability |
| `3` | Identity, role, policy, permission, delegation or privilege-administration capability, or explicitly unrestricted authorization such as `Action="*"` / `iam:*` |
| `unknown` | Applicable but statement, Effect, Action, or Action capability cannot be determined reliably from static evidence |
| `not_applicable` | The feature is not meaningful for the finding according to the approved applicability matrix |

## Separation from resource scope

Resource scope must not independently determine
`privilege_impact`.

Wildcard, scoped, or unresolved Resource information is represented
through the appropriate resource-scope contextual feature such as
`wildcard_resource`.

This separation avoids encoding the same contextual dimension in
both `privilege_impact` and resource-scope features.

## Multiple Actions

Each resolved Action in the relevant statement is classified
independently and the maximum privilege capability is used.

If unresolved Action evidence could change the resulting level, the
result is `unknown`.

If a resolved Action already establishes level `3`, an additional
unresolved Action cannot increase the ordinal level beyond `3`.

## Effect and Condition

A deterministically identified `Effect = "Deny"` statement maps to
level `0`.

An unresolved Effect maps to `unknown`.

Conditions do not automatically reduce the level because this
feature captures potential capability rather than complete effective
runtime authorization.

Conditions should remain traceable in evidence where available.

## Action taxonomy

The operational Action taxonomy for levels `1`, `2`, and `3` must
be deterministic, version-controlled, and auditable.

An Action that cannot be classified by the approved taxonomy must
produce `unknown`; it must not silently default to a lower level.

The taxonomy must be defined independently of human risk labels,
model predictions, or experimental performance.

---

# Context Feature Evidence Contract — Normative Clarification

> [!IMPORTANT]
> This section is normative.
>
> Finding-level contextual features used in the research dataset must
> follow D-009.

Each accepted contextual feature observation must be supported by
deterministic and auditable static evidence.

The approved representation uses shared finding/source provenance
combined with feature-level decision evidence.

A determined value must preserve sufficient observed facts,
references, method/version information, and decision basis to make
the conclusion independently auditable.

A negative observation must be supported by evidence over the
relevant analysis scope. Failure to observe positive evidence is not
sufficient proof of a negative state.

`unknown` represents genuine static-analysis uncertainty for an
applicable feature. It must preserve the reason for uncertainty.

Parser failures, missing source artifacts, extractor errors, or other
operational failures must not be silently represented as `unknown`;
they are data-quality or extraction failures.

`not_applicable` is established by the approved applicability
contract and requires applicability provenance rather than fabricated
source evidence.

Scanner findings may contribute evidence but do not alone establish
contextual feature values when the value claims a property of the
Terraform configuration or infrastructure context.

Evidence may use explicit Terraform configuration, deterministic
cross-resource relationships within the candidate artifact, scanner
metadata, and approved versioned taxonomies.

Provider/runtime defaults must not be silently materialized as
explicit evidence unless their use has been separately specified and
versioned.

IAM evidence must conform to D-007 and D-008.

Resource-role classification must use a version-controlled mapping.

The evidence representation itself must be versioned so that
research outputs remain reproducible and auditable.

---

# Resource Role Taxonomy — Normative Clarification

> [!IMPORTANT]
> This section is normative and follows D-010.

`resource_role` is a deterministic type-level contextual feature
representing the functional security domain of a Terraform object.

It does not infer business purpose, data sensitivity, workload
criticality, or runtime importance.

The allowed roles remain:

- `identity`
- `primary_data`
- `logging`
- `network`
- `compute`
- `other`

The operational mapping must be explicit and version-controlled.

`other` is an explicitly approved category for recognized resource
types; it is not a fallback for missing or unknown types.

Empty, unreadable, or unmapped resource types in an in-scope finding
constitute extraction/data-quality failures.

Research-scope filtering precedes contextual-feature extraction, so
raw scanner findings outside the approved research rule scope do not
require contextual feature observations.

The exact v1 mappings are recorded by D-010 and the corresponding
version-controlled taxonomy artifact.

---

# Network Context Semantics — Normative Clarification

> [!IMPORTANT]
> This section is normative and follows D-011.

The network contextual features intentionally represent different
properties.

`reachability` represents statically configured network reachability
of the resource or network control associated with the finding.

`internet_exposure` represents direct inbound Internet exposure.

`public_access` represents statically demonstrated public
accessibility of the affected resource.

These properties must not be collapsed.

A subnet that is deterministically associated with a route table
containing a default route to an Internet Gateway may be classified
as `reachability=internet`.

That fact alone does not establish direct Internet exposure or public
access of a workload in the subnet.

Likewise, an applicable egress security-group rule whose configured
destination is Internet-wide may establish
`reachability=internet` for the rule without proving that a runtime
workload is attached to that security group.

Missing preventive controls are not positive evidence of public
access.

Unknown network observations must preserve both the path elements
that were successfully resolved and the exact static relationship
that remains unresolved.

Evidence v1 unknown observations must use the approved deterministic
reason codes recorded in D-011.

Operational extraction failures remain distinct from research
uncertainty.

---

# S3 Static Public-Access Evidence — Normative Clarification

> [!IMPORTANT]
> This section is normative and follows D-012.

For an applicable S3 finding, `public_access` measures public access
demonstrated by the Terraform candidate, not effective deployed or
runtime access. Account-level, organization-level, provider-default,
and externally managed state is not inferred from absence in the
candidate.

`yes` requires an affected-bucket public ACL (`public-read` or
`public-read-write`) with explicit `block_public_acls=false` and
`ignore_public_acls=false`, or an affected-bucket policy containing a
resolved public `Allow` grant without an unsupported `Condition` and
with explicit `block_public_policy=false` and
`restrict_public_buckets=false`. One complete, unblocked mechanism is
sufficient.

`no` requires positive preventive evidence: an explicit, resolved
Public Access Block for the affected bucket with all four flags set
to `true`. Missing ACL, policy, or Public Access Block is not negative
evidence. Partial, unresolved, conflicting, or unsupported controls
leave the value `unknown` when neither a complete public mechanism nor
the all-four-flag preventive proof applies. `not_applicable` remains
determined by the applicability matrix.

The complete decision contract, including affected-bucket scope and
evidence requirements, is recorded in D-012.

---

## Normative Clarification — D-013 Phase-4 Benchmark Identity and Scope

This clarification records the accepted Phase-4 benchmark identity
and scope contract.

The frozen Feature Spec v1.0 finding population is the authoritative
input population from which the Phase-4 Tier-3 Prioritization
Benchmark is constructed.

The benchmark identity hierarchy is:

`source_id`
→ `source_task_id`
→ `family_id`
→ `artifact_id`
→ `scenario_id`
→ `finding_id`

For the current GenIaC population:

- `source_id` identifies GenIaC-SecBench;
- `source_task_id` preserves the upstream infrastructure task;
- `artifact_id` corresponds to the frozen candidate artifact;
- `family_id` groups artifacts with sufficiently close task,
  infrastructure intent, controlled base, or lineage to create a
  leakage risk;
- `scenario_id` identifies one selected artifact under one explicit
  approved business-context assignment;
- `finding_id` remains the frozen Feature Spec v1.0 finding
  identifier.

The upstream GenIaC task/scenario identifier is therefore not
automatically the final evaluation scenario identifier.

Tier-3 benchmark sampling is performed at family/artifact level,
never by independently sampling individual findings.

If an artifact/scenario is selected, all of its in-scope frozen
findings are retained. Findings are not truncated merely to reduce
annotation effort or force a desired scenario size.

Scenarios with at least three findings are preferred for ranking
evaluation, and scenarios with at least five findings are preferred
where practical for NDCG@5 eligibility.

Business context is explicit scenario metadata and is not inferred
from resource names, filenames, model names, scanner output, human
labels, baseline results, or model predictions.

The exact scenario context assignments are intentionally left
unresolved until a separate Phase-4 context-assignment protocol is
approved.

The historical CTX annotation stream is not merged into the main
Feature Spec v1.0 benchmark. It may only be used as a separately
identified secondary contrastive-context dataset.

Controlled Context A/B analysis remains secondary. Context variants
belonging to the same technical lineage remain within the same
`family_id` and must not cross evaluation partitions.

D-013 freezes benchmark identity and construction semantics only.
It does not yet freeze the selected Tier-3 artifact list, business
context assignments, annotator packet visibility policy, human
ranking, ML target encoding, or final validation split strategy.

---

## Normative Clarification — D-014 Tier-3 Benchmark Selection and Family Boundary

For the current GenIaC-SecBench Feature Spec v1.0 population,
artifacts generated from the same exact upstream infrastructure task
are treated as one leakage family.

Different upstream tasks are not merged solely because they share
resource types, numerical suffixes, or broad infrastructure themes.

The main Tier-3 Prioritization Benchmark uses the predefined
artifact-level eligibility rule:

`artifact_finding_count >= 3`

The rule selects 40 artifacts containing 300 frozen findings.

Under the accepted task-based family boundary, these artifacts span
10 families and preserve coverage of all 10 research-scope rules and
all 9 research-scope resource types.

Selection is performed before human annotation and before any
baseline or ML result is observed.

All in-scope frozen findings of a selected artifact are retained.

Artifacts containing only one or two findings remain part of the
frozen Phase-3 research population but are not included in the main
Tier-3 human-ranking benchmark.

The selected technical artifact is not by itself a final evaluation
scenario. A final scenario requires one explicit approved business
context according to D-013.

Family-level grouping remains mandatory for later experimental
partitioning.
