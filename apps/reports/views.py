from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from apps.monitoring.models import Container, MonthlyContainerMetric
from django.db.models import Sum

@login_required
def consumption_report(request):
    # Total consumption per container for the last 6 months
    monthly_stats = MonthlyContainerMetric.objects.all().order_by('-timestamp')
    
    # Group by container
    report_data = {}
    for stat in monthly_stats:
        c_id = stat.container_id
        if c_id not in report_data:
            report_data[c_id] = {
                'container': stat.container,
                'months': []
            }
        report_data[c_id]['months'].append(stat)
        
    context = {
        'report_data': report_data.values(),
    }
    return render(request, 'reports/consumption.html', context)
