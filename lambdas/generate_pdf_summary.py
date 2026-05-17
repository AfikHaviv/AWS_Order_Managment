import boto3
import json
import os
from datetime import datetime, timezone
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import cm
import io

s3 = boto3.client('s3')
BUCKET = os.environ['BUCKET_NAME']

def lambda_handler(event, context):
    # Step 1: Read all TXT files from S3
    response = s3.list_objects_v2(Bucket=BUCKET, Prefix='backups/')
    objects = response.get('Contents', [])

    orders = []
    for obj in objects:
        txt = s3.get_object(Bucket=BUCKET, Key=obj['Key'])
        content = txt['Body'].read().decode('utf-8')
        orders.append(parse_txt(content))

    # Step 2: Build PDF
    pdf_buffer = io.BytesIO()
    build_pdf(pdf_buffer, orders)
    pdf_buffer.seek(0)

    # Step 3: Save to S3
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    key = f"summaries/summary_{timestamp}.pdf"
    s3.put_object(
        Bucket=BUCKET,
        Key=key,
        Body=pdf_buffer.getvalue(),
        ContentType='application/pdf'
    )

    # Step 4: Generate pre-signed URL
    url = s3.generate_presigned_url(
        'get_object',
        Params={'Bucket': BUCKET, 'Key': key},
        ExpiresIn=3600
    )

    return {
        'statusCode': 200,
        'headers': {'Access-Control-Allow-Origin': '*'},
        'body': json.dumps({'pdf_url': url})
    }


def parse_txt(content):
    order = {}
    for line in content.strip().split('\n'):
        if ':' in line:
            key, _, value = line.partition(':')
            order[key.strip()] = value.strip()
    return order


def build_pdf(buffer, orders):
    doc = SimpleDocTemplate(buffer, pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm)

    styles = getSampleStyleSheet()
    story = []

    # Title
    title_style = ParagraphStyle('Title',
        fontName='Helvetica-Bold', fontSize=18,
        textColor=colors.HexColor('#232F3E'),
        alignment=1, spaceAfter=6)
    sub_style = ParagraphStyle('Sub',
        fontName='Helvetica', fontSize=10,
        textColor=colors.grey, alignment=1, spaceAfter=20)

    story.append(Paragraph('Deleted Orders Summary', title_style))
    story.append(Paragraph(
        f'Generated: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}  |  Total: {len(orders)} orders',
        sub_style))

    if not orders:
        story.append(Paragraph('No deleted orders found.', styles['Normal']))
        doc.build(story)
        return

    # Table
    headers = ['Order ID', 'Description', 'Price', 'Created', 'Deleted At']
    th_style = ParagraphStyle('TH', fontName='Helvetica-Bold',
        fontSize=8, textColor=colors.white)
    td_style = ParagraphStyle('TD', fontName='Helvetica',
        fontSize=7.5, leading=11)

    data = [[Paragraph(h, th_style) for h in headers]]
    for o in orders:
        data.append([
            Paragraph(o.get('Order ID', 'N/A')[:8] + '...', td_style),
            Paragraph(o.get('Description', 'N/A'), td_style),
            Paragraph(str(o.get('Price', 'N/A')), td_style),
            Paragraph(o.get('Creation Date', 'N/A')[:10], td_style),
            Paragraph(o.get('Deleted At', 'N/A')[:10], td_style),
        ])

    W = A4[0] - 4*cm
    col_widths = [W*0.25, W*0.30, W*0.12, W*0.17, W*0.16]
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#232F3E')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F5F5F5')]),
        ('GRID', (0,0), (-1,-1), 0.4, colors.HexColor('#CCCCCC')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t)
    doc.build(story)