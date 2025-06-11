from django.shortcuts import render
from .bots import Openai_Bot, Anothrpic_Bot, Perplexity_Bot  # adjust path as needed
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json


openai_bot = Openai_Bot("data")
anthropic_bot = Anothrpic_Bot("data")
perplexity_bot = Perplexity_Bot("data")

bots = {
    'openai': openai_bot,
    'anthropic': anthropic_bot,
    'perplexity': perplexity_bot
}



def chatbot_view(request):
    bot_response = ""
    selected_bot = "openai"
    user_message = ""

    if request.method == "POST":
        selected_bot = request.POST.get("bot")
        user_message = request.POST.get("message")
        if user_message:
            thread_id = "abc123"
            state = {"messages": [{"type": "human", "content": user_message}]}

            result = bots[selected_bot].graph.invoke(
                state,
                config={
                    "configurable": {
                        "thread_id": thread_id
                    }
                }
            )
            bot_response = result["messages"][-1].content

    return render(request, "chat.html", {
        "bot_response": bot_response,
        "selected_bot": selected_bot,
        "user_message": user_message
    })


@csrf_exempt
def chatbot_response(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            user_input = data.get("message", "")
            if not user_input:
                return JsonResponse({"error": "No message provided"}, status=400)

            bot_response = bot.chat(user_input)  # Replace with the appropriate method call
            return JsonResponse({"response": bot_response})

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

    return JsonResponse({"error": "POST request required"}, status=405)
