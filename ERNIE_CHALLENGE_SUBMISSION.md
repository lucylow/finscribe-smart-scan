# 📄 FinScribe Smart Scan: AI-Powered Financial Document Intelligence

**🏆 Submitted for the ERNIE AI Developer Challenge: Best PaddleOCR-VL Fine-Tune & Best Agent System**

FinScribe Smart Scan is an enterprise-grade solution that transforms raw financial documents (invoices, statements) into validated, structured data in under 2 seconds. We leverage the unique capabilities of Baidu's AI ecosystem to solve the critical problem of financial data entry errors and high processing costs.

## ✨ Core Innovation: Semantic Document Understanding

Our solution moves beyond traditional OCR by integrating three cutting-edge AI components:

1.  **Fine-Tuned PaddleOCR-VL:** We fine-tuned the model to specialize in the complex, variable layouts of financial documents. This allows us to perform **layout-aware text recognition**, preserving the semantic relationship between labels and values (e.g., linking "Grand Total" to its corresponding number, regardless of position).
2.  **Unsloth-Optimized LLM Extraction:** A highly efficient, fine-tuned LLaMA model (optimized with Unsloth) processes the structured OCR output to extract data into a strict JSON schema, ensuring high accuracy and low latency.
3.  **CAMEL-AI Multi-Agent Validation:** A multi-agent system (built on the CAMEL-AI framework) acts as a virtual auditor, performing **arithmetic checks** (Subtotal + Tax = Total) and **business rule validation** to guarantee data integrity before human review.

## 🚀 Key Results & Value Proposition

| Metric | Traditional Manual Process | FinScribe Smart Scan | Impact |
| :--- | :--- | :--- | :--- |
| **Processing Time** | 5 - 10 minutes | **< 2 seconds** | 99% Time Reduction |
| **Field Accuracy** | ~90% (with human error) | **94.2%** (Field Extraction) | Enterprise-Grade Reliability |
| **Cost Per Document** | $12 - $40 | **Near Zero** (Automated) | Massive Operational Savings |

## 🛠️ Technical Stack

*   **Frontend:** React, TypeScript, TailwindCSS (Professional, Human-in-the-Loop Correction UI)
*   **Backend:** Python (FastAPI/Flask), Supabase (Auth, Database, Edge Functions)
*   **AI/ML:** PaddleOCR-VL (Fine-Tuned), LLaMA (Unsloth-Optimized), CAMEL-AI (Validation Agents)
*   **MLOps:** Active Learning Loop (Human corrections feed directly into the fine-tuning pipeline)

## 💡 Why FinScribe Should Win

FinScribe Smart Scan is a perfect demonstration of the ERNIE AI Developer Challenge's goals:

*   **Best PaddleOCR-VL Fine-Tune:** We showcase a sophisticated, domain-specific fine-tune that exploits PaddleOCR-VL's unique layout-understanding capabilities to solve a real-world business problem that generic OCR cannot.
*   **Best Agent System:** We utilize the CAMEL-AI framework to build a critical validation layer, proving the power of multi-agent systems in ensuring data integrity.

## 🔗 Live Demo & Repository

*   **Live Application:** [https://finscribe-smart-scan.lovable.app/](https://finscribe-smart-scan.lovable.app/)
*   **Code Repository:** [https://github.com/lucylow/finscribe-smart-scan](https://github.com/lucylow/finscribe-smart-scan)

---
*Developed for the ERNIE AI Developer Challenge.*

