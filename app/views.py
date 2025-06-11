from django.shortcuts import render
from .bots import Openai_Bot, Anothrpic_Bot, Perplexity_Bot  # adjust path as needed
from django.http import JsonResponse, HttpResponseBadRequest
from django.conf import settings
import json
import re
import os
import uuid


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
    retrieved_docs = []
    selected_bot = "openai"
    user_message = ""

    if request.method == "POST":
        selected_bot = request.POST.get("bot")
        user_message = request.POST.get("message")
        config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        if user_message:
            streamed_steps = []
            for step in bots[selected_bot].graph.stream(
                {"messages": [{"role": "user", "content": user_message}]},
                stream_mode="values",
                config=config,
            ):
                streamed_steps.append(step)
                # step["messages"][-1].pretty_print()
            matches = []
            if streamed_steps:
                # Assuming the final message is in the last streamed step
                bot_response = streamed_steps[-1]["messages"][-1].content
                source_string = streamed_steps[-1]["messages"][2].content
                print("source:", source_string)
                matches = re.findall(
                    r"metadata=\{[^}]*'source': '([^']+)'[^}]*\}.*?page_content='(.*?)'\)",
                    source_string,
                    re.DOTALL)
    return render(request, "chat.html", {
        "bot_response": bot_response,
        "selected_bot": selected_bot,
        "user_message": user_message,
        "matches": matches,
    })




def get_file_content(request):
    source_path = request.GET.get("source")
    
    if not source_path:
        return HttpResponseBadRequest("Missing source parameter.")

    data_dir = os.path.join(settings.BASE_DIR, "app", "data")
    full_path = os.path.normpath(os.path.join(data_dir, os.path.basename(source_path)))
    print("looking for file at:", full_path)
    if not full_path.startswith(data_dir):
        return HttpResponseBadRequest("Invalid file path.")

    if not os.path.exists(full_path):
        return JsonResponse({"error": "File not found."}, status=404)

    try:
        with open(full_path, "r", encoding="utf-8") as f:
            data = json.load(f)  # parse JSON
    except json.JSONDecodeError:
        return JsonResponse({"error": "File is not valid JSON."}, status=400)
    except Exception as e:
        return JsonResponse({"error": f"Error reading file: {str(e)}"}, status=500)
    return JsonResponse(data)
