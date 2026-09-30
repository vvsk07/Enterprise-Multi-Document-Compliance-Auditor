"""
Streamlit Dashboard for Document Ingestion, NLP Analysis, FAISS Semantic Search & RAG Assistant.
Connects to FastAPI backend running on http://127.0.0.1:8000.
"""

import streamlit as st
import requests

API_BASE_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="Enterprise Compliance Auditor",
    page_icon="⚖️",
    layout="wide"
)

st.title("⚖️ Enterprise Multi-Document Intelligence & Compliance Auditor")
st.caption("Phase 4: Sentence-Transformers, FAISS Vector Indexing, Semantic Search & Evidence RAG")

# Sidebar Status & Index Check
st.sidebar.header("System Connection & Vector Index")
try:
    health_res = requests.get(f"{API_BASE_URL}/health", timeout=3)
    if health_res.status_code == 200:
        st.sidebar.success("Backend Connected (FastAPI)")
    else:
        st.sidebar.error("Backend Error")

    index_res = requests.get(f"{API_BASE_URL}/index/status", timeout=3)
    if index_res.status_code == 200:
        idx_info = index_res.json()
        st.sidebar.markdown("---")
        st.sidebar.markdown("**Vector Store Status**")
        st.sidebar.write(f"• **Indexed Chunks**: {idx_info['indexed_chunks']}")
        st.sidebar.write(f"• **Embedding Model**: {idx_info['embedding_model']}")
        st.sidebar.write(f"• **Vector Dimension**: {idx_info['embedding_dimension']}")
        st.sidebar.write(f"• **Index Type**: {idx_info['index_type']}")
        
        if st.sidebar.button("Rebuild Vector Index"):
            with st.spinner("Rebuilding FAISS Index..."):
                rb_res = requests.post(f"{API_BASE_URL}/index/rebuild")
                if rb_res.status_code == 200:
                    st.sidebar.success("Index Rebuilt Successfully!")
                    st.rerun()
except Exception:
    st.sidebar.warning("Backend Offline (Run `uvicorn app.main:app`)")

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11, tab12, tab13, tab14, tab15 = st.tabs([
    "📤 Upload Documents",
    "📚 Document Library",
    "🔎 Document Inspector",
    "🧠 NLP Pipeline",
    "🔍 Semantic Search",
    "💬 RAG Assistant",
    "📋 Compliance Audit",
    "⚙️ Compliance Rules",
    "🔀 Contradiction Detection",
    "📊 Risk & Audit Dashboard",
    "⚡ Advanced Hybrid Search",
    "🧠 RAG Trace",
    "🛡️ Security & System Health",
    "📈 Performance",
    "📋 Audit Logs"
])




# TAB 1: UPLOAD DOCUMENTS
with tab1:
    st.subheader("Upload Business Documents")
    st.markdown("Supported formats: **PDF (.pdf)**, **DOCX (.docx)**, **TXT (.txt)** (Max 25 MB per file)")
    
    uploaded_files = st.file_uploader(
        "Select document files to upload, process, and index:",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True
    )

    if st.button("Upload & Index Documents", type="primary"):
        if not uploaded_files:
            st.warning("Please select at least one file to upload.")
        else:
            with st.spinner("Uploading, ingesting, classifying, extracting entities, and indexing vectors..."):
                files_payload = []
                for file in uploaded_files:
                    files_payload.append(
                        ("files", (file.name, file.getvalue(), file.type or "application/octet-stream"))
                    )

                try:
                    res = requests.post(f"{API_BASE_URL}/documents/upload", files=files_payload)
                    if res.status_code == 201:
                        data = res.json()
                        st.success(data.get("message", "Upload and indexing successful!"))
                        
                        if data.get("uploaded_files"):
                            st.subheader("Successfully Processed & Indexed Files")
                            st.table(data["uploaded_files"])
                            
                        if data.get("failed_files"):
                            st.subheader("Failed Files")
                            st.warning(data["failed_files"])
                    else:
                        st.error(f"Upload failed: {res.text}")
                except Exception as e:
                    st.error(f"Error connecting to backend API: {e}")

# TAB 2: DOCUMENT LIBRARY
with tab2:
    st.subheader("Ingested Document Repository")
    if st.button("Refresh Repository"):
        st.rerun()

    try:
        res = requests.get(f"{API_BASE_URL}/documents")
        if res.status_code == 200:
            docs = res.json()
            if docs:
                table_data = []
                for d in docs:
                    table_data.append({
                        "Document ID": d["document_id"][:8],
                        "Filename": d["filename"],
                        "Type": d["file_type"].upper(),
                        "Status": d["document_status"],
                        "Category": d.get("predicted_document_type", "Unclassified"),
                        "Confidence": f"{d.get('classification_confidence', 0.0) or 0.0:.2%}",
                        "Pages": d["page_count"],
                        "Chunks": d["chunks_count"],
                        "Entities": d.get("entities_count", 0),
                        "OCR Req.": d["ocr_required"]
                    })
                st.table(table_data)
            else:
                st.info("No documents uploaded yet. Go to the Upload tab to add files.")
        else:
            st.error("Failed to fetch documents list.")
    except Exception as e:
        st.error(f"Backend API error: {e}")

# TAB 3: DOCUMENT INSPECTOR
with tab3:
    st.subheader("Document Content & Chunk Inspector")
    try:
        res = requests.get(f"{API_BASE_URL}/documents")
        if res.status_code == 200:
            docs = res.json()
            if docs:
                doc_options = {f"{d['filename']} ({d['document_id'][:8]})": d['document_id'] for d in docs}
                selected_label = st.selectbox("Select document to inspect:", list(doc_options.keys()), key="inspect_select")
                selected_id = doc_options[selected_label]

                if selected_id:
                    doc_res = requests.get(f"{API_BASE_URL}/documents/{selected_id}")
                    if doc_res.status_code == 200:
                        detail = doc_res.json()
                        col1, col2, col3, col4 = st.columns(4)
                        col1.metric("Category", detail.get("predicted_document_type", "Unclassified"))
                        col2.metric("Confidence", f"{detail.get('classification_confidence', 0.0) or 0.0:.2%}")
                        col3.metric("Page Count", detail["page_count"])
                        col4.metric("Chunks", len(detail.get("chunks", [])))

                        st.markdown("#### Extracted Raw Text Preview")
                        st.text_area("Extracted Text", detail.get("extracted_text", "")[:3000], height=200)

                        st.markdown("#### Generated Chunks")
                        chunks = detail.get("chunks", [])
                        if chunks:
                            for c in chunks:
                                with st.expander(f"Chunk #{c['chunk_index']} | Page {c.get('page_number') or 'N/A'} | Section: {c.get('section') or 'General'}"):
                                    st.write(c["text"])
                                    st.json(c.get("metadata", {}))
                        else:
                            st.info("No chunks generated for this document.")
            else:
                st.info("No documents available.")
    except Exception as e:
        st.error(f"Error fetching document details: {e}")

# TAB 4: NLP PIPELINE
with tab4:
    st.subheader("🧠 NLP Analysis & Named Entity Inspection")
    try:
        res = requests.get(f"{API_BASE_URL}/documents")
        if res.status_code == 200:
            docs = res.json()
            if docs:
                doc_options = {f"{d['filename']} ({d['document_id'][:8]})": d['document_id'] for d in docs}
                nlp_selected_label = st.selectbox("Select document for NLP analysis:", list(doc_options.keys()), key="nlp_select")
                nlp_selected_id = doc_options[nlp_selected_label]

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Run Document Classification"):
                        with st.spinner("Classifying document..."):
                            cls_res = requests.post(f"{API_BASE_URL}/documents/{nlp_selected_id}/classify")
                            if cls_res.status_code == 200:
                                st.success("Classification completed!")
                                st.json(cls_res.json())
                            else:
                                st.error(cls_res.text)
                with col2:
                    if st.button("Run Entity Extraction (NER)"):
                        with st.spinner("Extracting entities via spaCy..."):
                            ent_res = requests.post(f"{API_BASE_URL}/documents/{nlp_selected_id}/entities")
                            if ent_res.status_code == 200:
                                st.success("Entity extraction completed!")
                            else:
                                st.error(ent_res.text)

                if nlp_selected_id:
                    ent_fetch_res = requests.get(f"{API_BASE_URL}/documents/{nlp_selected_id}/entities")
                    if ent_fetch_res.status_code == 200:
                        ent_data = ent_fetch_res.json()
                        st.markdown(f"### Extracted Entities ({ent_data['total_entities']})")
                        entities = ent_data.get("entities", [])
                        if entities:
                            label_filter = st.multiselect(
                                "Filter by Entity Type:",
                                options=list(set(e["entity_label"] for e in entities)),
                                default=list(set(e["entity_label"] for e in entities))
                            )
                            filtered_ents = [e for e in entities if e["entity_label"] in label_filter]
                            
                            ent_table = []
                            for e in filtered_ents:
                                ent_table.append({
                                    "Entity Text": e["entity_text"],
                                    "Label": e["entity_label"],
                                    "Normalized": e["normalized_text"],
                                    "Start": e["start_position"],
                                    "End": e["end_position"],
                                    "Context": e.get("context", "")[:100]
                                })
                            st.table(ent_table)
                        else:
                            st.info("No entities extracted yet for this document.")
            else:
                st.info("No documents available for NLP analysis.")
    except Exception as e:
        st.error(f"NLP Dashboard Error: {e}")

# TAB 5: SEMANTIC SEARCH
with tab5:
    st.subheader("🔍 Dense Vector Semantic Search")
    st.markdown("Search across all document chunks using **Sentence-Transformers (`all-MiniLM-L6-v2`)** and **FAISS** vector similarity.")

    col_q, col_k = st.columns([4, 1])
    with col_q:
        search_query = st.text_input("Enter search query:", placeholder="e.g. What are the termination notice conditions?", key="search_q")
    with col_k:
        top_k_val = st.slider("Top K Results:", min_value=1, max_value=20, value=5, key="search_k")

    if st.button("Search Documents", type="primary"):
        if not search_query.strip():
            st.warning("Please enter a search query.")
        else:
            with st.spinner("Embedding query and searching FAISS index..."):
                try:
                    search_res = requests.post(
                        f"{API_BASE_URL}/search",
                        json={"query": search_query, "top_k": top_k_val}
                    )
                    if search_res.status_code == 200:
                        s_data = search_res.json()
                        st.markdown(f"### Results for: *'{s_data['query']}'* (Found {s_data['total_results']})")
                        
                        results = s_data.get("results", [])
                        if results:
                            for idx, item in enumerate(results, 1):
                                score_pct = item['score'] * 100
                                badge = "🟢 High Match" if item['score'] >= 0.5 else "🟡 Moderate Match"
                                
                                with st.container():
                                    st.markdown(f"#### #{idx} {item['filename']} | {badge} | Similarity Score: `{item['score']:.4f}`")
                                    st.caption(f"Page: {item.get('page_number') or 'N/A'} | Section: {item.get('section') or 'General'} | Category: {item.get('document_type', 'N/A')}")
                                    st.info(item['text'])
                                    st.divider()
                        else:
                            st.info("No relevant document chunks found matching the query.")
                    else:
                        st.error(f"Search failed: {search_res.text}")
                except Exception as e:
                    st.error(f"Search API Error: {e}")

# TAB 6: RAG ASSISTANT
with tab6:
    st.subheader("💬 Evidence-Grounded RAG Assistant")
    st.markdown("Ask questions about uploaded documents. Answers are **strictly grounded in retrieved evidence** with traceable citations.")

    col_rag_q, col_rag_k = st.columns([4, 1])
    with col_rag_q:
        rag_query = st.text_input("Enter question about your documents:", placeholder="e.g. What is the confidentiality requirement and data retention period?", key="rag_q")
    with col_rag_k:
        rag_k_val = st.slider("Context Chunks:", min_value=1, max_value=10, value=5, key="rag_k")

    if st.button("Ask RAG Assistant", type="primary"):
        if not rag_query.strip():
            st.warning("Please enter a question.")
        else:
            with st.spinner("Retrieving evidence and synthesizing grounded answer..."):
                try:
                    rag_res = requests.post(
                        f"{API_BASE_URL}/rag/query",
                        json={"query": rag_query, "top_k": rag_k_val, "minimum_score": 0.20}
                    )
                    if rag_res.status_code == 200:
                        r_data = rag_res.json()
                        
                        st.markdown("### Answer")
                        st.success(r_data["answer"])

                        st.markdown("### Traceable Sources & Citations")
                        citations = r_data.get("citations", [])
                        if citations:
                            for c in citations:
                                st.markdown(f"• **{c}**")
                        
                        st.markdown("### Retrieved Context Chunks")
                        sources = r_data.get("sources", [])
                        if sources:
                            for s in sources:
                                with st.expander(f"[{s['citation_index']}] {s['filename']} | Score: {s['relevance_score']:.4f} | Page {s.get('page_number') or 'N/A'}"):
                                    st.write(s["text"])
                        else:
                            st.info("No context chunks retrieved.")
                    else:
                        st.error(f"RAG query failed: {rag_res.text}")
                except Exception as e:
                    st.error(f"RAG API Error: {e}")

# TAB 7: COMPLIANCE AUDIT
with tab7:
    st.subheader("📋 Automated Document Compliance Auditor")
    st.markdown("Audits documents against configured compliance rules using **hybrid deterministic checks** and **dense vector semantic retrieval**.")

    try:
        res = requests.get(f"{API_BASE_URL}/documents")
        if res.status_code == 200:
            docs = res.json()
            if docs:
                doc_options = {f"{d['filename']} ({d['document_id'][:8]}) [{d.get('predicted_document_type', 'Unclassified')}]": d['document_id'] for d in docs}
                audit_selected_label = st.selectbox("Select document to audit:", list(doc_options.keys()), key="audit_select")
                audit_selected_id = doc_options[audit_selected_label]

                col_btn, col_btn_all = st.columns([2, 2])
                with col_btn:
                    run_audit = st.button("Run Compliance Audit", type="primary")

                if run_audit:
                    with st.spinner("Evaluating compliance rules and retrieving evidence..."):
                        audit_res = requests.post(f"{API_BASE_URL}/documents/{audit_selected_id}/compliance")
                        if audit_res.status_code == 200:
                            st.success("Compliance audit completed successfully!")
                        else:
                            st.error(f"Audit failed: {audit_res.text}")

                # Fetch and display findings
                summary_res = requests.get(f"{API_BASE_URL}/documents/{audit_selected_id}/compliance/summary")
                if summary_res.status_code == 200:
                    summary = summary_res.json()
                    
                    st.markdown(f"### Audit Summary: **{summary['document_name']}** (`{summary['document_type']}`)")
                    
                    c1, c2, c3, c4, c5, c6 = st.columns(6)
                    c1.metric("Total Rules", summary["total_rules"])
                    c2.metric("Applicable", summary["applicable_rules"])
                    c3.metric("Passed 🟢", summary["passed"])
                    c4.metric("Failed 🔴", summary["failed"])
                    c5.metric("Review 🟠", summary["needs_review"])
                    c6.metric("N/A ⚪", summary["not_applicable"])

                    st.divider()

                    findings = summary.get("findings", [])
                    if findings:
                        status_filter = st.radio(
                            "Filter Findings by Status:",
                            ["ALL", "FAIL", "NEEDS_REVIEW", "PASS", "NOT_APPLICABLE"],
                            horizontal=True
                        )

                        filtered_findings = findings
                        if status_filter != "ALL":
                            filtered_findings = [f for f in findings if f["status"] == status_filter]

                        st.markdown(f"#### Compliance Findings ({len(filtered_findings)})")

                        status_color = {
                            "PASS": "🟢 PASS",
                            "FAIL": "🔴 FAIL",
                            "NEEDS_REVIEW": "🟠 NEEDS REVIEW",
                            "NOT_APPLICABLE": "⚪ NOT APPLICABLE"
                        }

                        for f in filtered_findings:
                            st_badge = status_color.get(f["status"], f["status"])
                            with st.expander(f"{st_badge} | {f['rule_id']} - {f['title']} | Severity: {f['severity']}"):
                                st.markdown(f"**Explanation**: {f['explanation']}")
                                
                                if f.get("evidence_text"):
                                    st.markdown("**Retrieved Evidence:**")
                                    st.info(f["evidence_text"])
                                    
                                if f.get("page_number") or f.get("section") or f.get("relevance_score"):
                                    st.caption(f"Source: {f.get('source_filename', 'N/A')} | Page: {f.get('page_number') or 'N/A'} | Section: {f.get('section') or 'General'} | Relevance Score: {f.get('relevance_score') or 0.0:.4f}")
                                    
                                if f.get("remediation"):
                                    st.warning(f"**Remediation Recommendation:** {f['remediation']}")
                    else:
                        st.info("No compliance audit executed yet for this document. Click 'Run Compliance Audit' above.")
            else:
                st.info("No documents uploaded yet.")
    except Exception as e:
        st.error(f"Compliance Audit UI Error: {e}")

# TAB 8: COMPLIANCE RULES
with tab8:
    st.subheader("⚙️ Configured Compliance Rules")
    st.markdown("Rules loaded from `configs/compliance_rules.json`. Edit the JSON configuration to modify or add rules.")

    if st.button("Reload Rules Configuration"):
        try:
            rl_res = requests.post(f"{API_BASE_URL}/compliance/rules/reload")
            if rl_res.status_code == 200:
                st.success("Rules reloaded successfully!")
                st.rerun()
            else:
                st.error(f"Failed to reload rules: {rl_res.text}")
        except Exception as e:
            st.error(f"Reload Error: {e}")

    try:
        rules_res = requests.get(f"{API_BASE_URL}/compliance/rules")
        if rules_res.status_code == 200:
            rules = rules_res.json()
            st.markdown(f"### Loaded Rules Count: **{len(rules)}**")
            
            rules_table = []
            for r in rules:
                rules_table.append({
                    "Rule ID": r["rule_id"],
                    "Name": r["name"],
                    "Category": r.get("category", "General"),
                    "Severity": r.get("severity", "MEDIUM"),
                    "Target Doc Types": ", ".join(r.get("document_types") or r.get("required_for", [])),
                    "Eval Type": r.get("evaluation", {}).get("type", "presence"),
                    "Enabled": r.get("enabled", True)
                })
            st.table(rules_table)

            for r in rules:
                with st.expander(f"Details: {r['rule_id']} - {r['name']}"):
                    st.write(f"**Description**: {r['description']}")
                    st.write(f"**Requirement**: {r['requirement']}")
                    st.write(f"**Keywords**: {', '.join(r.get('keywords', []))}")
                    st.write(f"**Patterns**: {r.get('patterns', [])}")
                    st.write(f"**Remediation**: {r.get('remediation', '')}")
        else:
            st.error("Failed to load rules.")
    except Exception as e:
        st.error(f"Rules UI Error: {e}")

# TAB 9: CONTRADICTION DETECTION
with tab9:
    st.subheader("🔀 Cross-Document Contradiction Detection Engine")
    st.markdown("Identifies conflicting factual, legal, and policy requirements across multi-document repositories using **dense vector candidate search** and **deterministic fact extraction**.")

    # Pairwise comparison & repository detection controls
    try:
        res = requests.get(f"{API_BASE_URL}/documents")
        if res.status_code == 200:
            docs = res.json()
            if docs:
                doc_opts = {f"{d['filename']} ({d['document_id'][:8]})": d['document_id'] for d in docs}
                
                col_btn, col_p1, col_p2 = st.columns([2, 3, 3])
                with col_btn:
                    st.write("")
                    run_detect = st.button("🔍 Detect Contradictions", type="primary")

                with col_p1:
                    doc_a_label = st.selectbox("Document A (Pairwise Compare):", list(doc_opts.keys()), key="pair_a_sel")
                with col_p2:
                    doc_b_label = st.selectbox("Document B (Pairwise Compare):", list(doc_opts.keys()), index=min(1, len(doc_opts)-1), key="pair_b_sel")

                col_cmp, _ = st.columns([2, 4])
                with col_cmp:
                    run_pair_cmp = st.button("Compare Two Documents")

                if run_detect:
                    with st.spinner("Searching repository candidate chunk pairs and evaluating facts..."):
                        det_res = requests.post(f"{API_BASE_URL}/contradictions/detect", json={})
                        if det_res.status_code == 200:
                            st.success("Repository contradiction analysis completed successfully!")
                        else:
                            st.error(f"Detection failed: {det_res.text}")

                if run_pair_cmp:
                    id_a = doc_opts[doc_a_label]
                    id_b = doc_opts[doc_b_label]
                    with st.spinner(f"Comparing '{doc_a_label}' vs '{doc_b_label}'..."):
                        cmp_res = requests.post(
                            f"{API_BASE_URL}/contradictions/compare",
                            json={"document_a_id": id_a, "document_b_id": id_b}
                        )
                        if cmp_res.status_code == 200:
                            st.success(f"Pairwise comparison completed! Found {len(cmp_res.json())} contradiction(s).")
                        else:
                            st.error(f"Pairwise comparison failed: {cmp_res.text}")
    except Exception as e:
        st.error(f"Controls Error: {e}")

    st.divider()

    # Metrics & Visualizations
    try:
        report_res = requests.get(f"{API_BASE_URL}/contradictions")
        if report_res.status_code == 200:
            report = report_res.json()
            contradictions = report.get("contradictions", [])
            
            confirmed_cnt = sum(1 for c in contradictions if c.get("status") == "CONFIRMED")
            potential_cnt = sum(1 for c in contradictions if c.get("status") == "POTENTIAL")
            high_sev = report.get("severity_metrics", {}).get("high", 0)
            med_sev = report.get("severity_metrics", {}).get("medium", 0)
            low_sev = report.get("severity_metrics", {}).get("low", 0)

            c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
            c1.metric("Docs Analyzed", report.get("total_documents_analyzed", 0))
            c2.metric("Total Conflicts", report.get("total_contradictions_detected", 0))
            c3.metric("Confirmed 🟢", confirmed_cnt)
            c4.metric("Potential 🟠", potential_cnt)
            c5.metric("High Severity 🔴", high_sev)
            c6.metric("Med Severity 🟧", med_sev)
            c7.metric("Low Severity 🟡", low_sev)

            st.divider()

            if contradictions:
                col_chart1, col_chart2 = st.columns(2)
                with col_chart1:
                    st.markdown("##### Contradictions by Type")
                    type_counts = report.get("type_breakdown", {})
                    if type_counts:
                        st.bar_chart(type_counts)
                with col_chart2:
                    st.markdown("##### Contradictions by Severity")
                    st.bar_chart({"High": high_sev, "Medium": med_sev, "Low": low_sev})

                st.markdown(f"### Detailed Contradiction Findings ({len(contradictions)})")

                for idx, c in enumerate(contradictions, 1):
                    sev_badge = "🔴 HIGH" if c["severity"] == "HIGH" else "🟠 MEDIUM"
                    status_badge = f"[{c.get('status', 'CONFIRMED')}]"
                    
                    with st.expander(f"#{idx} {status_badge} Topic: {c['topic']} | Type: {c['contradiction_type']} | {sev_badge} | Score: {c.get('contradiction_score', 0.0):.2f}"):
                        st.markdown(f"**Explanation**: {c['explanation']}")
                        
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.markdown(f"📄 **Document A**: `{c.get('source_a') or c.get('source_filename_a', 'N/A')}`")
                            st.caption(f"Page: {c.get('page_a') or 'N/A'} | Section: {c.get('section_a') or 'General'}")
                            st.write(f"**Extracted Value**: `{c.get('value_a') or 'N/A'}`")
                            st.info(c.get("evidence_a") or c.get("statement_a", ""))

                        with col_b:
                            st.markdown(f"📄 **Document B**: `{c.get('source_b') or c.get('source_filename_b', 'N/A')}`")
                            st.caption(f"Page: {c.get('page_b') or 'N/A'} | Section: {c.get('section_b') or 'General'}")
                            st.write(f"**Extracted Value**: `{c.get('value_b') or 'N/A'}`")
                            st.warning(c.get("evidence_b") or c.get("statement_b", ""))

                        # Status update control
                        col_st_up, _ = st.columns([3, 3])
                        with col_st_up:
                            new_st = st.selectbox(
                                "Update Status:",
                                ["CONFIRMED", "POTENTIAL", "REVIEWED", "DISMISSED"],
                                index=["CONFIRMED", "POTENTIAL", "REVIEWED", "DISMISSED"].index(c.get("status", "CONFIRMED")) if c.get("status") in ["CONFIRMED", "POTENTIAL", "REVIEWED", "DISMISSED"] else 0,
                                key=f"st_up_{c['contradiction_id']}"
                            )
                            if st.button("Save Status", key=f"btn_st_{c['contradiction_id']}"):
                                up_r = requests.patch(f"{API_BASE_URL}/contradictions/{c['contradiction_id']}/status", json={"status": new_st})
                                if up_r.status_code == 200:
                                    st.success(f"Status updated to '{new_st}'!")
                                    st.rerun()
                                else:
                                    st.error(f"Update failed: {up_r.text}")
            else:
                st.info("No cross-document contradictions detected yet. Click '🔍 Detect Contradictions' above.")
        else:
            st.error("Failed to load contradiction report.")
    except Exception as e:
        st.error(f"Contradictions UI Error: {e}")


# TAB 10: RISK & AUDIT DASHBOARD
with tab10:
    st.subheader("📊 Executive Risk & Audit Dashboard")
    st.caption("Explainable multi-component risk scoring, evidence traceability, recommendations, and PDF/CSV/JSON report exports.")

    # Action Toolbar
    col_act1, col_act2, col_act3, col_act4 = st.columns(4)
    with col_act1:
        if st.button("🔄 Recalculate Portfolio Risk", type="primary", use_container_width=True):
            with st.spinner("Recalculating risk assessments for all documents..."):
                r_res = requests.post(f"{API_BASE_URL}/risk/recalculate")
                if r_res.status_code == 200:
                    st.success("Risk assessments recalculated!")
                    st.rerun()
                else:
                    st.error(f"Recalculation failed: {r_res.text}")

    with col_act2:
        try:
            json_report_res = requests.get(f"{API_BASE_URL}/reports/audit/json", timeout=3)
            if json_report_res.status_code == 200:
                st.download_button(
                    "📥 Export JSON Audit Report",
                    data=json_report_res.text,
                    file_name="compliance_audit_report.json",
                    mime="application/json",
                    use_container_width=True
                )
        except Exception:
            pass

    with col_act3:
        try:
            csv_report_res = requests.get(f"{API_BASE_URL}/reports/audit/csv?export_type=risk_assessments", timeout=3)
            if csv_report_res.status_code == 200:
                st.download_button(
                    "📥 Export CSV Risk Assessments",
                    data=csv_report_res.text,
                    file_name="risk_assessments_report.csv",
                    mime="text/csv",
                    use_container_width=True
                )
        except Exception:
            pass

    with col_act4:
        try:
            pdf_report_res = requests.get(f"{API_BASE_URL}/reports/audit/pdf", timeout=5)
            if pdf_report_res.status_code == 200:
                st.download_button(
                    "📄 Download PDF Audit Report",
                    data=pdf_report_res.content,
                    file_name="compliance_audit_report.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
        except Exception:
            pass

    st.divider()

    # Executive Overview KPIs
    try:
        overview_res = requests.get(f"{API_BASE_URL}/risk/overview")
        if overview_res.status_code == 200:
            ov = overview_res.json()
            c1, c2, c3, c4, c5, c6 = st.columns(6)
            c1.metric("Audited Documents", ov.get("total_documents", 0))
            c2.metric("Portfolio Score", f"{ov.get('portfolio_risk_score', 0.0):.1f} / 100")
            c3.metric("Portfolio Level", ov.get("portfolio_risk_level", "LOW"))
            c4.metric("High / Critical Risk", ov.get("high_risk_documents_count", 0) + ov.get("critical_risk_documents_count", 0))
            c5.metric("Avg Document Risk", f"{ov.get('average_risk_score', 0.0):.1f}")
            c6.metric("Median Risk", f"{ov.get('median_risk_score', 0.0):.1f}")

            st.divider()

            # Risk Visualizations
            col_v1, col_v2 = st.columns(2)
            with col_v1:
                st.markdown("##### Portfolio Risk Distribution")
                dist = ov.get("risk_distribution", {})
                if dist:
                    st.bar_chart(dist)

            with col_v2:
                st.markdown("##### Most Frequent Failed Compliance Rules")
                top_fails = ov.get("most_frequent_failed_rules", [])
                if top_fails:
                    chart_data = {item["rule_id"]: item["failure_count"] for item in top_fails}
                    st.bar_chart(chart_data)
                else:
                    st.info("No compliance rule failures logged.")

            st.divider()

            # Document Risk Inspector
            st.markdown("### 🔍 Document Risk Inspector & Breakdown")
            docs_res = requests.get(f"{API_BASE_URL}/documents")
            if docs_res.status_code == 200:
                doc_list = docs_res.json()
                if doc_list:
                    doc_options = {f"{d['filename']} ({d['document_id'][:8]}...)": d['document_id'] for d in doc_list}
                    selected_doc_label = st.selectbox("Select Document to Inspect:", list(doc_options.keys()), key="risk_inspector_sel")
                    selected_doc_id = doc_options[selected_doc_label]

                    risk_res = requests.get(f"{API_BASE_URL}/documents/{selected_doc_id}/risk")
                    if risk_res.status_code == 200:
                        risk_data = risk_res.json()

                        # Risk Header Cards
                        col_r1, col_r2 = st.columns([1, 2])
                        with col_r1:
                            lvl_color = "🔴" if risk_data['risk_level'] in ["HIGH", "CRITICAL"] else ("🟠" if risk_data['risk_level'] == "MEDIUM" else "🟢")
                            st.metric("Overall Document Risk Score", f"{risk_data['risk_score']} / 100", f"{lvl_color} {risk_data['risk_level']}")
                        with col_r2:
                            st.markdown("##### Weighted Risk Score Breakdown")
                            comps = risk_data.get("components", {})
                            c_comp = comps.get("compliance", {})
                            c_contra = comps.get("contradiction", {})
                            c_sev = comps.get("severity", {})
                            c_rev = comps.get("review", {})

                            st.write(f"• **Compliance Component** (45%): `Raw: {c_comp.get('raw_score', 0.0)}` → `Weighted: {c_comp.get('weighted_score', 0.0)}`")
                            st.write(f"• **Contradiction Component** (30%): `Raw: {c_contra.get('raw_score', 0.0)}` → `Weighted: {c_contra.get('weighted_score', 0.0)}`")
                            st.write(f"• **Severity Component** (15%): `Raw: {c_sev.get('raw_score', 0.0)}` → `Weighted: {c_sev.get('weighted_score', 0.0)}`")
                            st.write(f"• **Review Component** (10%): `Raw: {c_rev.get('raw_score', 0.0)}` → `Weighted: {c_rev.get('weighted_score', 0.0)}`")

                        st.markdown("#### 💡 Why is this document assigned this score?")
                        risk_factors = risk_data.get("risk_factors", [])
                        for factor in risk_factors:
                            st.warning(f"• {factor}")

                        st.markdown("#### 📋 Recommended Actions")
                        recs = risk_data.get("recommendations", [])
                        if recs:
                            st.table(recs)
                        else:
                            st.info("No actionable recommendations for this document.")
                    else:
                        st.error(f"Failed to fetch document risk: {risk_res.text}")
                else:
                    st.info("No documents uploaded yet.")
        else:
            st.error("Failed to load portfolio risk overview.")
    except Exception as e:
        st.error(f"Risk Dashboard Error: {e}")


# TAB 11: ADVANCED HYBRID SEARCH
with tab11:
    st.subheader("⚡ Advanced Hybrid BM25 + FAISS Search")
    st.markdown("Combines **BM25 Lexical Keyword** matching with **FAISS Dense Semantic** similarity and normalized candidate fusion.")

    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        hybrid_query = st.text_input("Enter hybrid search query:", placeholder="e.g. 30 days termination notice vendor contract", key="hyb_q")
    with col_h2:
        top_k_hyb = st.number_input("Top K Candidates:", min_value=1, max_value=20, value=5, key="top_k_hyb")

    c_w1, c_w2 = st.columns(2)
    with c_w1:
        bm25_w = st.slider("BM25 Lexical Weight:", 0.0, 1.0, 0.40, 0.05, key="bm25_w")
    with c_w2:
        dense_w = st.slider("FAISS Semantic Weight:", 0.0, 1.0, 0.60, 0.05, key="dense_w")

    if st.button("Execute Hybrid Search", type="primary", key="btn_hyb"):
        if not hybrid_query.strip():
            st.warning("Please enter a search query.")
        else:
            with st.spinner("Searching lexical BM25 index & FAISS dense vector store..."):
                try:
                    res = requests.post(
                        f"{API_BASE_URL}/search/hybrid",
                        json={
                            "query": hybrid_query,
                            "top_k": top_k_hyb,
                            "bm25_weight": bm25_w,
                            "dense_weight": dense_w
                        }
                    )
                    if res.status_code == 200:
                        data = res.json()
                        st.success(f"Found {data['total_results']} hybrid candidates.")
                        for item in data.get("results", []):
                            with st.expander(f"📄 {item['filename']} — Hybrid Score: {item.get('hybrid_score', item.get('score', 0.0)):.4f}"):
                                st.write(f"• **Chunk ID**: `{item.get('chunk_id')}`")
                                st.write(f"• **Raw BM25 Score**: `{item.get('raw_bm25', 0.0)}` | **Norm BM25**: `{item.get('norm_bm25', 0.0)}`")
                                st.write(f"• **Raw FAISS Score**: `{item.get('raw_dense', 0.0)}` | **Norm FAISS**: `{item.get('norm_dense', 0.0)}`")
                                st.markdown(f"> {item.get('text')}")
                    else:
                        st.error(f"Search failed: {res.text}")
                except Exception as e:
                    st.error(f"Error executing hybrid search: {e}")


# TAB 12: RAG TRACE
with tab12:
    st.subheader("🧠 Grounded RAG Execution & Candidate Trace")
    st.markdown("Visualizes full end-to-end multi-stage pipeline: **Query Analysis -> Candidate Fusion -> Cross-Encoder Reranking -> Citations**.")

    rag_trace_query = st.text_input("Enter RAG Question:", value="What is the vendor termination notice period?", key="rag_trace_q")
    if st.button("Run Advanced RAG & Trace", type="primary", key="btn_rag_trace"):
        with st.spinner("Executing Advanced RAG Pipeline..."):
            try:
                res = requests.post(f"{API_BASE_URL}/rag/advanced", json={"query": rag_trace_query, "top_k": 5})
                if res.status_code == 200:
                    data = res.json()
                    st.markdown("### 💬 Grounded Extractive Answer")
                    st.success(data["answer"])
                    st.write(f"**Confidence Level**: `{data['confidence'] * 100:.1f}%`")

                    st.markdown("### 📊 Multi-Stage Retrieval Trace")
                    trace = data.get("retrieval", {})
                    col_t1, col_t2, col_t3, col_t4 = st.columns(4)
                    col_t1.metric("BM25 Candidates", trace.get("bm25_candidates", 0))
                    col_t2.metric("FAISS Candidates", trace.get("dense_candidates", 0))
                    col_t3.metric("Fused Candidates", trace.get("fused_candidates", 0))
                    col_t4.metric("Reranked Top-K", trace.get("reranked_candidates", 0))

                    st.markdown("### 📚 Grounded Document Citations")
                    for cite in data.get("citations", []):
                        st.write(f"• {cite}")

                    st.markdown("### 🔬 Reranked Evidence Sources")
                    for src in data.get("sources", []):
                        with st.expander(f"[{src['citation_index']}] {src['filename']} — Reranker Score: {src.get('reranker_score', src.get('score', 0.0)):.4f}"):
                            st.write(f"• **BM25 Raw**: `{src.get('bm25_score', 0.0)}` | **FAISS Raw**: `{src.get('dense_score', 0.0)}`")
                            st.markdown(f"> {src.get('text')}")
                else:
                    st.error(f"RAG failed: {res.text}")
            except Exception as e:
                st.error(f"RAG Error: {e}")


# TAB 13: SECURITY & SYSTEM HEALTH
with tab13:
    st.subheader("🛡️ Security & System Health Monitor")
    if st.button("Refresh System Health", key="btn_health"):
        st.rerun()

    try:
        health_res = requests.get(f"{API_BASE_URL}/health")
        if health_res.status_code == 200:
            h_data = health_res.json()
            st.success(f"System Status: **{h_data.get('status', 'healthy').upper()}** (Version: {h_data.get('version', '8.0.0')})")
            
            st.markdown("#### Component Health Breakdown")
            comps = h_data.get("components", {})
            col_c1, col_c2, col_c3, col_c4, col_c5 = st.columns(5)
            col_c1.metric("Database (SQLite)", comps.get("database", "N/A"))
            col_c2.metric("FAISS Index", comps.get("faiss", "N/A"))
            col_c3.metric("BM25 Index", comps.get("bm25", "N/A"))
            col_c4.metric("Embeddings Model", comps.get("embeddings", "N/A"))
            col_c5.metric("Cross Reranker", comps.get("reranker", "N/A"))
        else:
            st.error("Health check returned error status.")
    except Exception as e:
        st.error(f"Health monitor offline: {e}")


# TAB 14: PERFORMANCE
with tab14:
    st.subheader("📈 System Latency & Telemetry Metrics")
    try:
        metrics_res = requests.get(f"{API_BASE_URL}/metrics")
        if metrics_res.status_code == 200:
            m_data = metrics_res.json()
            st.markdown("#### Application Telemetry Counters")
            st.json(m_data.get("counters", {}))

            st.markdown("#### Measured Latencies (P50 & P95)")
            lats = m_data.get("latencies", {})
            if lats:
                st.table(lats)
            else:
                st.info("No latency observations recorded yet.")
        else:
            st.error("Failed to load metrics.")
    except Exception as e:
        st.error(f"Metrics error: {e}")


# TAB 15: AUDIT LOGS
with tab15:
    st.subheader("📋 Application & Security Audit Log Viewer")
    col_a1, col_a2 = st.columns(2)
    with col_a1:
        filter_endpoint = st.text_input("Filter by Endpoint:", placeholder="/documents/upload", key="audit_ep")
    with col_a2:
        filter_action = st.text_input("Filter by Action:", placeholder="DOCUMENT_UPLOAD", key="audit_act")

    if st.button("Query Audit Logs", key="btn_audit"):
        try:
            params = {}
            if filter_endpoint:
                params["endpoint"] = filter_endpoint
            if filter_action:
                params["action"] = filter_action
            
            logs_res = requests.get(f"{API_BASE_URL}/audit/logs", params=params)
            if logs_res.status_code == 200:
                logs_data = logs_res.json()
                st.write(f"Total Logged Events: **{logs_data.get('total', 0)}**")
                st.table(logs_data.get("logs", []))
            else:
                st.error(f"Failed to fetch audit logs: {logs_res.text}")
        except Exception as e:
            st.error(f"Audit log error: {e}")





