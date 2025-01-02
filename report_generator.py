from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from datetime import datetime

def generate_student_report(student, fees, filename):
    """Generate a PDF report for a student's fee details"""
    doc = SimpleDocTemplate(filename, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30
    )
    elements.append(Paragraph('Student Fee Report', title_style))
    elements.append(Spacer(1, 20))

    # Student Details
    student_details = [
        ['Student Details', ''],
        ['Name:', student.name],
        ['Seat Number:', student.seat_number],
        ['Phone Number:', student.phone_number],
        ['Joining Date:', student.joining_date.strftime('%Y-%m-%d')],
        ['Monthly Fee:', f'₹{student.monthly_fee:.2f}']
    ]
    
    student_table = Table(student_details, colWidths=[2*inch, 4*inch])
    student_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(student_table)
    elements.append(Spacer(1, 20))

    # Fee Records
    if fees:
        fee_data = [['Month', 'Amount', 'Status', 'Payment Date']]
        for fee in fees:
            status = 'Paid' if fee.paid else 'Unpaid'
            payment_date = fee.payment_date.strftime('%Y-%m-%d') if fee.payment_date else '-'
            fee_data.append([
                fee.month.strftime('%B %Y'),
                f'₹{fee.amount:.2f}',
                status,
                payment_date
            ])
        
        fee_table = Table(fee_data, colWidths=[2*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        fee_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10)
        ]))
        elements.append(Paragraph('Fee Records', styles['Heading2']))
        elements.append(fee_table)
    else:
        elements.append(Paragraph('No fee records found.', styles['Normal']))

    doc.build(elements)
    return filename

def generate_monthly_report(fees_data, target_date, filename):
    """Generate a PDF report for all fees in a specific month"""
    doc = SimpleDocTemplate(filename, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30
    )
    title = f'Monthly Fee Report - {target_date.strftime("%B %Y")}'
    elements.append(Paragraph(title, title_style))
    elements.append(Spacer(1, 20))

    # Summary
    total_amount = sum(fee.amount for fee, _ in fees_data)
    paid_amount = sum(fee.amount for fee, _ in fees_data if fee.paid)
    unpaid_amount = total_amount - paid_amount
    paid_count = sum(1 for fee, _ in fees_data if fee.paid)
    unpaid_count = len(fees_data) - paid_count

    summary_data = [
        ['Summary', ''],
        ['Total Students:', len(fees_data)],
        ['Total Amount:', f'₹{total_amount:.2f}'],
        ['Paid Amount:', f'₹{paid_amount:.2f}'],
        ['Unpaid Amount:', f'₹{unpaid_amount:.2f}'],
        ['Paid Fees:', paid_count],
        ['Unpaid Fees:', unpaid_count]
    ]

    summary_table = Table(summary_data, colWidths=[2*inch, 4*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 20))

    # Fee Records
    if fees_data:
        fee_data = [['Student Name', 'Seat No.', 'Amount', 'Status', 'Payment Date']]
        for fee, student in fees_data:
            status = 'Paid' if fee.paid else 'Unpaid'
            payment_date = fee.payment_date.strftime('%Y-%m-%d') if fee.payment_date else '-'
            fee_data.append([
                student.name,
                student.seat_number,
                f'₹{fee.amount:.2f}',
                status,
                payment_date
            ])
        
        fee_table = Table(fee_data, colWidths=[2*inch, 1*inch, 1.5*inch, 1*inch, 1.5*inch])
        fee_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('ALIGN', (2, 1), (2, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10)
        ]))
        elements.append(Paragraph('Fee Records', styles['Heading2']))
        elements.append(fee_table)
    else:
        elements.append(Paragraph('No fee records found.', styles['Normal']))

    doc.build(elements)
    return filename
