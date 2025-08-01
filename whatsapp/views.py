from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
import json
import pandas as pd
import os
from datetime import datetime
from .models import WhatsAppMessage

VERIFY_TOKEN = 'my_secure_token'
EXCEL_FILE = 'whatsapp_messages.xlsx'

@csrf_exempt
def webhook(request):
    if request.method == 'GET':
        token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')
        if token == VERIFY_TOKEN:
            return HttpResponse(challenge)
        return HttpResponse("Invalid verification token", status=403)

    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            entry = data.get("entry", [])[0]
            change = entry.get("changes", [])[0]
            value = change.get("value", {})
            messages = value.get("messages", [])

            if messages:
                msg = messages[0]
                sender = msg.get("from")
                message_text = msg.get("text", {}).get("body", "")
                timestamp = datetime.fromtimestamp(int(msg.get("timestamp")))
                
                # 1. Save to Database
                WhatsAppMessage.objects.create(
                    sender=sender,
                    message=message_text,
                    timestamp=timestamp
                )
                
                # 2. Save to Excel
                row = {
                    "timestamp": timestamp,
                    "sender": sender,
                    "message": message_text
                }
                
                if os.path.exists(EXCEL_FILE):
                    df_existing = pd.read_excel(EXCEL_FILE)
                    df = pd.concat([df_existing, pd.DataFrame([row])], ignore_index=True)
                else:
                    df = pd.DataFrame([row])
                
                df.to_excel(EXCEL_FILE, index=False)

        except Exception as e:
            print("Error processing message:", e)
            return JsonResponse({
                "status": "error",
                "message": str(e)
            }, status=500)

        return JsonResponse({"status": "success"})