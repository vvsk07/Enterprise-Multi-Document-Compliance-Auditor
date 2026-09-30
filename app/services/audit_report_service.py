"""
Audit Report Generation Service for Enterprise Compliance Auditor.
Supports JSON export, CSV export, and professional ReportLab PDF report generation.
"""

import os
import io
import json
import logging
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

from app.config import settings
from app.models.document import Document, ComplianceFinding, ContradictionFinding, RiskAssessment
from app.services.risk_scoring_service import risk_scoring_service

logger = logging.getLogger(__name__)

REPORTS_DIR = settings.DATA_DIR / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

class AuditReportService:
    def generate_json_audit_report(self, db: Session, document_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Generates a comprehensive JSON audit report package.
        """
        portfolio = risk_scoring_service.calculate_portfolio_risk(db, document_ids)

        query_docs = db.query(Document)
        if document_ids:
            query_docs = query_docs.filter(Document.document_id.in_(document_ids))
        docs = query_docs.all()
        doc_ids = [d.document_id for d in docs]

        findings = db.query(ComplianceFinding).filter(ComplianceFinding.document_id.in_(doc_ids)).all() if doc_ids else []
        contradictions = db.query(ContradictionFinding).filter(
            (ContradictionFinding.document_a_id.in_(doc_ids)) |
            (ContradictionFinding.document_b_id.in_(doc_ids))
        ).all() if doc_ids else []
        assessments = db.query(RiskAssessment).filter(RiskAssessment.document_id.in_(doc_ids)).all() if doc_ids else []

        all_recommendations = []
        for ass in assessments:
            recs = json.loads(ass.recommendations_json) if ass.recommendations_json else []
            all_recommendations.extend(recs)

        return {
            "audit_metadata": {
                "title": "Enterprise Multi-Document Compliance & Risk Audit Report",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "environment": getattr(settings, "APP_ENV", "development"),
                "audited_documents_count": len(docs),
                "system_version": getattr(settings, "VERSION", "1.0.0")
            },
            "portfolio_summary": portfolio,
            "documents": [d.to_dict() for d in docs],
            "compliance_findings": [f.to_dict() for f in findings],
            "contradictions": [c.to_dict() for c in contradictions],
            "risk_assessments": [a.to_dict() for a in assessments],
            "recommendations": all_recommendations,
            "methodology": {
                "compliance_weight": "45%",
                "contradiction_weight": "30%",
                "severity_weight": "15%",
                "review_weight": "10%",
                "thresholds": "LOW (0-24.99), MEDIUM (25-49.99), HIGH (50-74.99), CRITICAL (75-100)"
            },
            "legal_disclaimer": "This automated compliance audit and risk assessment report is generated for informational and risk-triage purposes only and does not constitute formal legal counsel."
        }

    def generate_csv_audit_report(self, db: Session, export_type: str = "risk_assessments") -> str:
        """
        Generates CSV format audit data for risk assessments, compliance findings, or contradictions.
        """
        if export_type == "compliance_findings":
            findings = db.query(ComplianceFinding).all()
            data = [f.to_dict() for f in findings]
            df = pd.DataFrame(data)
        elif export_type == "contradictions":
            contras = db.query(ContradictionFinding).all()
            data = [c.to_dict() for c in contras]
            df = pd.DataFrame(data)
        else:
            assessments = db.query(RiskAssessment).all()
            data = []
            for a in assessments:
                doc = db.query(Document).filter(Document.document_id == a.document_id).first()
                d_dict = a.to_dict()
                d_dict["filename"] = doc.filename if doc else "Unknown"
                d_dict["document_type"] = doc.predicted_document_type if doc else "Unclassified"
                data.append(d_dict)
            df = pd.DataFrame(data)

        if df.empty:
            return ""

        output = io.StringIO()
        df.to_csv(output, index=False)
        return output.getvalue()

    def generate_pdf_audit_report(self, db: Session, output_path: Optional[str] = None, document_ids: Optional[List[str]] = None) -> str:
        """
        Generates a PDF audit report using ReportLab.
        """
        if not output_path:
            filename = f"audit_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            output_path = str(REPORTS_DIR / filename)

        json_data = self.generate_json_audit_report(db, document_ids)
        portfolio = json_data["portfolio_summary"]
        docs = json_data["documents"]
        findings = json_data["compliance_findings"]
        contradictions = json_data["contradictions"]
        assessments = json_data["risk_assessments"]
        recommendations = json_data["recommendations"]

        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36
        )

        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'DocTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=22,
            leading=26,
            textColor=colors.HexColor('#1E293B'),
            spaceAfter=6
        )

        subtitle_style = ParagraphStyle(
            'DocSubTitle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#64748B'),
            spaceAfter=15
        )

        h2_style = ParagraphStyle(
            'SectionH2',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=14,
            leading=18,
            textColor=colors.HexColor('#0F172A'),
            spaceBefore=12,
            spaceAfter=8
        )

        body_style = ParagraphStyle(
            'BodyTextCustom',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=13,
            textColor=colors.HexColor('#334155')
        )

        story = []

        # Header Title
        story.append(Paragraph("Enterprise Compliance & Risk Audit Report", title_style))
        story.append(Paragraph(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')} | Documents Audited: {len(docs)}", subtitle_style))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#2563EB'), spaceAfter=15))

        # 1. Executive Summary Table
        story.append(Paragraph("1. Executive Summary & Portfolio KPIs", h2_style))
        summary_table_data = [
            [
                Paragraph("<b>Portfolio Risk Score</b>", body_style),
                Paragraph(f"<b>{portfolio.get('portfolio_risk_score', 0.0)} / 100</b>", body_style),
                Paragraph("<b>Portfolio Risk Level</b>", body_style),
                Paragraph(f"<b>{portfolio.get('portfolio_risk_level', 'LOW')}</b>", body_style)
            ],
            [
                Paragraph("<b>Total Documents</b>", body_style),
                Paragraph(str(len(docs)), body_style),
                Paragraph("<b>High / Critical Risk Docs</b>", body_style),
                Paragraph(str(portfolio.get('high_risk_documents_count', 0) + portfolio.get('critical_risk_documents_count', 0)), body_style)
            ],
            [
                Paragraph("<b>Compliance Failures</b>", body_style),
                Paragraph(str(len([f for f in findings if f.get('status') == 'FAIL'])), body_style),
                Paragraph("<b>Policy Contradictions</b>", body_style),
                Paragraph(str(len(contradictions)), body_style)
            ]
        ]

        t_summary = Table(summary_table_data, colWidths=[1.75*inch, 1.75*inch, 1.75*inch, 1.75*inch])
        t_summary.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('PADDING', (0,0), (-1,-1), 6),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ]))
        story.append(t_summary)
        story.append(Spacer(1, 15))

        # 2. Document Risk Summary Table
        story.append(Paragraph("2. Document Risk Assessments", h2_style))
        doc_headers = ["Filename", "Category", "Risk Score", "Risk Level", "Failures", "Conflicts"]
        doc_rows = [[Paragraph(f"<b>{h}</b>", body_style) for h in doc_headers]]

        for ass in assessments:
            doc_info = next((d for d in docs if d["document_id"] == ass["document_id"]), {})
            fname = doc_info.get("filename", "Unknown")
            cat = doc_info.get("predicted_document_type", "Unclassified")
            score = str(ass.get("risk_score", 0.0))
            lvl = ass.get("risk_level", "LOW")
            fails = str(ass.get("compliance_fail_count", 0))
            contras = str(ass.get("confirmed_contradiction_count", 0) + ass.get("potential_contradiction_count", 0))

            doc_rows.append([
                Paragraph(fname[:25], body_style),
                Paragraph(cat, body_style),
                Paragraph(score, body_style),
                Paragraph(f"<b>{lvl}</b>", body_style),
                Paragraph(fails, body_style),
                Paragraph(contras, body_style)
            ])

        t_docs = Table(doc_rows, colWidths=[2.2*inch, 1.3*inch, 0.9*inch, 0.9*inch, 0.85*inch, 0.85*inch])
        t_docs.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#E2E8F0')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('PADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(t_docs)
        story.append(Spacer(1, 15))

        # 3. High Severity Compliance Failures
        story.append(Paragraph("3. Compliance Rule Failures", h2_style))
        fail_list = [f for f in findings if f.get("status") == "FAIL"]
        if fail_list:
            fail_headers = ["Rule ID", "Title", "Severity", "Document", "Explanation"]
            fail_rows = [[Paragraph(f"<b>{h}</b>", body_style) for h in fail_headers]]
            for f in fail_list[:10]:
                rule_id = str(f.get("rule_id") or "")
                title = str(f.get("title") or "")
                sev = str(f.get("severity") or "")
                src = str(f.get("source_filename") or "")[:20]
                expl = str(f.get("explanation") or "")[:80]
                fail_rows.append([
                    Paragraph(rule_id, body_style),
                    Paragraph(title, body_style),
                    Paragraph(sev, body_style),
                    Paragraph(src, body_style),
                    Paragraph(expl, body_style)
                ])
            t_fails = Table(fail_rows, colWidths=[0.9*inch, 1.5*inch, 0.8*inch, 1.3*inch, 2.5*inch])
            t_fails.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#FEE2E2')),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#FCA5A5')),
                ('PADDING', (0,0), (-1,-1), 4),
            ]))
            story.append(t_fails)
        else:
            story.append(Paragraph("No compliance rule failures detected.", body_style))

        story.append(Spacer(1, 15))

        # 4. Cross-Document Contradictions
        story.append(Paragraph("4. Cross-Document Policy Contradictions", h2_style))
        if contradictions:
            contra_headers = ["Topic", "Type", "Status", "Doc A Evidence", "Doc B Evidence"]
            contra_rows = [[Paragraph(f"<b>{h}</b>", body_style) for h in contra_headers]]
            for c in contradictions[:10]:
                doc_a_name = str(c.get('source_filename_a') or 'Doc A')
                doc_b_name = str(c.get('source_filename_b') or 'Doc B')
                stmt_a = str(c.get('statement_a') or '')[:40]
                stmt_b = str(c.get('statement_b') or '')[:40]
                ev_a = f"{doc_a_name}: {stmt_a}"
                ev_b = f"{doc_b_name}: {stmt_b}"
                contra_rows.append([
                    Paragraph(str(c.get("topic") or ""), body_style),
                    Paragraph(str(c.get("contradiction_type") or ""), body_style),
                    Paragraph(str(c.get("status") or ""), body_style),
                    Paragraph(ev_a, body_style),
                    Paragraph(ev_b, body_style)
                ])
            t_contras = Table(contra_rows, colWidths=[1.3*inch, 1.3*inch, 0.9*inch, 1.75*inch, 1.75*inch])
            t_contras.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#FEF3C7')),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#FDE047')),
                ('PADDING', (0,0), (-1,-1), 4),
            ]))
            story.append(t_contras)
        else:
            story.append(Paragraph("No cross-document contradictions detected.", body_style))

        story.append(Spacer(1, 15))

        # 5. Recommendations
        story.append(Paragraph("5. Recommended Action Items", h2_style))
        if recommendations:
            rec_headers = ["ID", "Priority", "Title", "Recommendation Action"]
            rec_rows = [[Paragraph(f"<b>{h}</b>", body_style) for h in rec_headers]]
            for r in recommendations[:10]:
                rec_rows.append([
                    Paragraph(str(r.get("recommendation_id") or ""), body_style),
                    Paragraph(str(r.get("priority") or ""), body_style),
                    Paragraph(str(r.get("title") or ""), body_style),
                    Paragraph(str(r.get("recommendation") or ""), body_style)
                ])
            t_recs = Table(rec_rows, colWidths=[0.8*inch, 0.9*inch, 1.8*inch, 3.5*inch])
            t_recs.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#E0F2FE')),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#7DD3FC')),
                ('PADDING', (0,0), (-1,-1), 4),
            ]))
            story.append(t_recs)
        else:
            story.append(Paragraph("No recommendations generated.", body_style))

        story.append(Spacer(1, 20))

        # 6. Legal Disclaimer & Methodology
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#CBD5E1'), spaceAfter=10))
        story.append(Paragraph("<b>Audit Methodology & Legal Disclaimer</b>", body_style))
        story.append(Paragraph(
            "Risk scores are calculated using a weighted formula (Compliance: 45%, Contradictions: 30%, Severity: 15%, Review: 10%). "
            "This automated report is designed for compliance triage and audit analysis. It does not replace professional legal counsel.",
            subtitle_style
        ))

        doc.build(story)
        logger.info(f"Generated PDF audit report at '{output_path}'.")
        return output_path


audit_report_service = AuditReportService()
