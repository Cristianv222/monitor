import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from apps.billing.models import Client
from apps.billing.tasks import calculate_days_difference

@csrf_exempt
def client_status_api(request):
    if request.method == 'GET':
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return JsonResponse({'error': 'Unauthorized', 'message': 'Missing or invalid Authorization header. Format must be: Bearer {token}'}, status=401)
            
        token = auth_header.split(' ')[1]
        
        try:
            client = Client.objects.get(api_token=token)
            sub = client.subscriptions.filter(status='active').first()
            
            if not sub:
                sub_susp = client.subscriptions.filter(status='suspended').first()
                if sub_susp:
                    return JsonResponse({
                        'client': client.name,
                        'status': 'suspended', 
                        'message': 'Your account is suspended due to non-payment.',
                        'days_left': 0
                    })
                return JsonResponse({'client': client.name, 'status': 'inactive', 'message': 'No active subscriptions found.', 'days_left': 0})
                
            days_left = calculate_days_difference(sub.cutoff_day)
            
            response_data = {
                'client': client.name,
                'status': 'active',
                'days_left': days_left,
                'message': f'You have {days_left} days left until cutoff.'
            }
            if days_left <= 5 and days_left > 0:
                response_data['alert'] = True
                response_data['message'] = f'Payment is due in {days_left} days. Please pay to avoid suspension.'
            elif days_left <= 0:
                response_data['alert'] = True
                response_data['message'] = 'Payment is PAST DUE. Suspension imminent.'
                
            return JsonResponse(response_data)
            
        except Client.DoesNotExist:
            return JsonResponse({'error': 'Unauthorized', 'message': 'Invalid API Token.'}, status=401)
        except Exception as e:
            return JsonResponse({'error': 'Server Error', 'message': str(e)}, status=500)
            
    return JsonResponse({'error': 'Method not allowed'}, status=405)
