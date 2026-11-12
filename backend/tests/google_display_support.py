from backend.research.provider import normalize_interaction
HTML='<style>.chip{color:green}</style><div class="chip"><a target="_blank" href="https://www.google.com/search?q=public">Public suggestion ORIGINAL</a></div>'
ANSWER='Google ephemeral answer marker.'
URL='https://research-evidence.example.org/once'
def google_result(request):
    data={'steps':[{'type':'google_search_call','arguments':{'queries':['public question']}},{'type':'google_search_result','result':[{'search_suggestions':HTML}]},{'type':'model_output','content':[{'type':'text','text':ANSWER,'annotations':[{'type':'url_citation','url':URL,'title':'Ephemeral title marker','start_index':0,'end_index':len(ANSWER)}]}]}]}
    return normalize_interaction(data,request,'gemini_google_search','gemini-3.8-flash',2,'google_search')
