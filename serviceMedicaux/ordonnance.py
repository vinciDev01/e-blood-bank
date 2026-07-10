"""Génération de l'ordonnance PDF d'une demande de sang (ReportLab + QR).

Rendu professionnel A4 : en-tête (logo, titre, référence, QR de vérification),
bloc établissement demandeur, bloc patient, tableau des détails de la demande,
zone cachet/signature, pied de page.
"""
from datetime import date
from io import BytesIO

import qrcode
from django.contrib.staticfiles import finders
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, HRFlowable,
)

ROUGE = colors.HexColor('#b91c1c')
GRIS = colors.HexColor('#64748b')
GRIS_CLAIR = colors.HexColor('#f1f5f9')
NOIR = colors.HexColor('#1e293b')


def _valeurs(donnees):
    """Aplatit les valeurs d'un JSONField indexé par email (tous rôles confondus)."""
    if not isinstance(donnees, dict):
        return [str(donnees)] if donnees else []
    out = []
    for v in donnees.values():
        if isinstance(v, (list, tuple)):
            out.extend(str(x) for x in v)
        elif v not in (None, ''):
            out.append(str(v))
    return out


def _qr_image(texte):
    """Retourne un BytesIO PNG du QR (utilisable directement par Platypus Image)."""
    qr = qrcode.make(texte)
    buf = BytesIO()
    qr.save(buf, format='PNG')
    buf.seek(0)
    return buf


def construire_pdf(demande):
    """Retourne les octets du PDF de l'ordonnance pour `demande`."""
    tampon = BytesIO()
    doc = SimpleDocTemplate(
        tampon, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
        title=f"Ordonnance {demande.reference()}",
    )

    styles = getSampleStyleSheet()
    st_titre = ParagraphStyle('titre', parent=styles['Title'], textColor=ROUGE,
                              fontSize=17, spaceAfter=2, leading=20)
    st_sous = ParagraphStyle('sous', parent=styles['Normal'], textColor=GRIS, fontSize=9)
    st_section = ParagraphStyle('section', parent=styles['Heading2'], textColor=NOIR,
                                fontSize=11, spaceBefore=10, spaceAfter=4)
    st_normal = ParagraphStyle('n', parent=styles['Normal'], textColor=NOIR, fontSize=9.5, leading=14)
    st_pied = ParagraphStyle('pied', parent=styles['Normal'], textColor=GRIS, fontSize=7.5, leading=10)

    elements = []
    service = demande.serviceMedicaux
    patient = demande.patient

    # --- En-tête : logo | titre+référence | QR ---
    logo_path = finders.find('img/Logo_eBloodBank.png')
    logo_flow = Image(logo_path, width=26 * mm, height=26 * mm) if logo_path else Paragraph('eBloodBank', st_titre)

    bloc_titre = [
        Paragraph('ORDONNANCE DE DEMANDE DE SANG', st_titre),
        Paragraph('eBloodBank - Système de gestion de banque de sang', st_sous),
        Spacer(1, 4),
        Paragraph(f"<b>Référence :</b> {demande.reference()}", st_normal),
        Paragraph(f"<b>Date de la demande :</b> {demande.date_demande or date.today()}", st_normal),
    ]

    qr_flow = Image(_qr_image(demande.reference()), width=24 * mm, height=24 * mm)

    entete = Table([[logo_flow, bloc_titre, qr_flow]], colWidths=[30 * mm, 100 * mm, 28 * mm])
    entete.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
    ]))
    elements.append(entete)
    elements.append(Spacer(1, 6))
    elements.append(HRFlowable(width='100%', thickness=1.2, color=ROUGE))

    # --- Établissement demandeur ---
    elements.append(Paragraph('Établissement demandeur', st_section))
    if service:
        infos = [
            ('Nom', service.nom_etablissement),
            ('Responsable', getattr(service, 'responsable', '') or '—'),
            ('Adresse', f"{getattr(service, 'adresse', '') or ''}, {getattr(service, 'ville', '') or ''}".strip(', ')),
            ('Téléphone', getattr(service, 'telephone', '') or '—'),
            ('Email', service.email or '—'),
        ]
    else:
        infos = [('Demandeur', 'Particulier / Donneur')]
    elements.append(_table_infos(infos))

    # --- Patient ---
    if patient:
        elements.append(Paragraph('Patient', st_section))
        elements.append(_table_infos([
            ('Nom complet', patient.nom_complet or '—'),
            ('Date de naissance', str(patient.date_de_naissance) if patient.date_de_naissance else '—'),
            ('Groupe sanguin', patient.groupe_sanguin or '—'),
        ]))

    # --- Détails de la demande ---
    elements.append(Paragraph('Détails de la demande', st_section))
    groupes = ', '.join(_valeurs(demande.groupe_sanguin)) or '—'
    poches = ', '.join(_valeurs(demande.nombre_poches)) or '—'
    entetes = ['Type de produit', 'Groupe(s) sanguin(s)', 'Nombre de poches', 'Urgence', 'Motif', 'État']
    valeurs = [demande.type_produit or '—', groupes, poches,
               demande.urgence or '—', demande.motif or '—', demande.etat or '—']
    tableau = Table([entetes, valeurs], colWidths=[32 * mm, 30 * mm, 26 * mm, 24 * mm, 24 * mm, 24 * mm])
    tableau.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), ROUGE),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, GRIS_CLAIR]),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(tableau)

    # --- Cachet / signature ---
    elements.append(Spacer(1, 22))
    sign = Table([[
        Paragraph("Cachet et signature du responsable<br/><br/><br/>_____________________________", st_normal),
        Paragraph(f"Fait le {date.today()}<br/><br/><br/>_____________________________", st_normal),
    ]], colWidths=[85 * mm, 85 * mm])
    sign.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')]))
    elements.append(sign)

    # --- Pied de page ---
    elements.append(Spacer(1, 16))
    elements.append(HRFlowable(width='100%', thickness=0.6, color=GRIS))
    elements.append(Paragraph(
        f"Document généré électroniquement par eBloodBank le {date.today()}. "
        f"Référence {demande.reference()} vérifiable via le QR code ci-dessus. "
        "Ce document ne constitue pas une prescription médicale nominative.",
        st_pied,
    ))

    doc.build(elements)
    return tampon.getvalue()


def _table_infos(paires):
    """Petit tableau à deux colonnes (libellé gras / valeur) pour un bloc d'infos."""
    st = ParagraphStyle('cell', fontSize=9.5, textColor=NOIR, leading=13)
    lignes = [[Paragraph(f"<b>{k}</b>", st), Paragraph(str(v), st)] for k, v in paires]
    t = Table(lignes, colWidths=[40 * mm, 130 * mm])
    t.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (0, -1), 0),
    ]))
    return t
