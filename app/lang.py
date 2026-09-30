"""Languages, categories and multilingual request templates.

The templates seed a realistic demo dataset and power the offline (no-API-key)
fallback analyser. With a Gemini key, live requests in *any* wording or language
are understood by Gemini instead.
"""
import re

LANGUAGES = {
    "hi": {"name": "Hindi", "native": "हिन्दी", "bcp47": "hi-IN"},
    "te": {"name": "Telugu", "native": "తెలుగు", "bcp47": "te-IN"},
    "ta": {"name": "Tamil", "native": "தமிழ்", "bcp47": "ta-IN"},
    "kn": {"name": "Kannada", "native": "ಕನ್ನಡ", "bcp47": "kn-IN"},
    "ml": {"name": "Malayalam", "native": "മലയാളം", "bcp47": "ml-IN"},
    "bn": {"name": "Bengali", "native": "বাংলা", "bcp47": "bn-IN"},
    "mr": {"name": "Marathi", "native": "मराठी", "bcp47": "mr-IN"},
    "gu": {"name": "Gujarati", "native": "ગુજરાતી", "bcp47": "gu-IN"},
    "or": {"name": "Odia", "native": "ଓଡ଼ିଆ", "bcp47": "or-IN"},
    "pa": {"name": "Punjabi", "native": "ਪੰਜਾਬੀ", "bcp47": "pa-IN"},
    "as": {"name": "Assamese", "native": "অসমীয়া", "bcp47": "as-IN"},
    "ur": {"name": "Urdu", "native": "اردو", "bcp47": "ur-IN"},
    "en": {"name": "English", "native": "English", "bcp47": "en-IN"},
}

STATE_LANGUAGE = {
    "Andhra Pradesh": "te", "Telangana": "te", "Tamil Nadu": "ta", "Puducherry": "ta", "Karnataka": "kn",
    "Kerala": "ml", "Maharashtra": "mr", "Goa": "mr", "Gujarat": "gu",
    "Dadra and Nagar Haveli and Daman and Diu": "gu", "West Bengal": "bn", "Tripura": "bn", "Odisha": "or",
    "Assam": "as", "Punjab": "pa", "Rajasthan": "hi", "Uttar Pradesh": "hi", "Bihar": "hi", "Jharkhand": "hi",
    "Madhya Pradesh": "hi", "Chhattisgarh": "hi", "Haryana": "hi", "Delhi": "hi", "Uttarakhand": "hi",
    "Himachal Pradesh": "hi", "Jammu and Kashmir": "ur", "Ladakh": "hi", "Andaman and Nicobar Islands": "hi",
    "Arunachal Pradesh": "en", "Meghalaya": "en", "Mizoram": "en", "Nagaland": "en", "Manipur": "en", "Sikkim": "en",
}

# category -> (label, flagship scheme, real NFHS-5 indicator used to measure the gap or None)
CATEGORIES = {
    "water": ("Drinking water", "Jal Jeevan Mission", "Population with an improved drinking-water source"),
    "sanitation": ("Sanitation & waste", "Swachh Bharat Mission", "Population using an improved sanitation facility"),
    "power": ("Electricity", "RDSS / Saubhagya", "Population living in households with electricity"),
    "health": ("Health facilities", "National Health Mission", "Institutional births"),
    "education": ("Schools & education", "Samagra Shiksha", "Females age 6+ who ever attended school"),
    "roads": ("Roads & connectivity", "PMGSY", None),
    "digital": ("Digital connectivity", "BharatNet", None),
}

# Each variant: English meaning + the same request in several languages.
TEMPLATES = {
    "water": [
        {"urgency": 5, "summary": "Drinking water outage for 3 weeks; handpump broken",
         "en": "No drinking water has reached our village for three weeks; the handpump is broken.",
         "texts": {
            "hi": "हमारे गाँव में तीन हफ्तों से पीने का पानी नहीं आया है, हैंडपंप खराब पड़ा है।",
            "te": "మా గ్రామానికి మూడు వారాలుగా తాగునీరు రావడం లేదు, చేతి పంపు పాడైపోయింది.",
            "ta": "எங்கள் கிராமத்திற்கு மூன்று வாரங்களாக குடிநீர் வரவில்லை, கை பம்பு பழுதாகிவிட்டது.",
            "kn": "ನಮ್ಮ ಹಳ್ಳಿಗೆ ಮೂರು ವಾರಗಳಿಂದ ಕುಡಿಯುವ ನೀರು ಬಂದಿಲ್ಲ, ಕೈಪಂಪು ಕೆಟ್ಟುಹೋಗಿದೆ.",
            "ml": "ഞങ്ങളുടെ ഗ്രാമത്തിൽ മൂന്നാഴ്ചയായി കുടിവെള്ളം എത്തിയിട്ടില്ല, കൈപ്പമ്പ് കേടായി.",
            "bn": "আমাদের গ্রামে তিন সপ্তাহ ধরে পানীয় জল আসেনি, টিউবওয়েল খারাপ হয়ে গেছে।",
            "mr": "आमच्या गावात तीन आठवड्यांपासून पिण्याचे पाणी आलेले नाही, हातपंप बंद पडला आहे.",
            "gu": "અમારા ગામમાં ત્રણ અઠવાડિયાથી પીવાનું પાણી આવ્યું નથી, હેન્ડપંપ બગડી ગયો છે.",
            "or": "ଆମ ଗାଁକୁ ତିନି ସପ୍ତାହ ହେଲା ପିଇବା ପାଣି ଆସିନାହିଁ, ହ୍ୟାଣ୍ଡପମ୍ପ ଖରାପ ହୋଇଯାଇଛି।",
            "pa": "ਸਾਡੇ ਪਿੰਡ ਵਿੱਚ ਤਿੰਨ ਹਫ਼ਤਿਆਂ ਤੋਂ ਪੀਣ ਵਾਲਾ ਪਾਣੀ ਨਹੀਂ ਆਇਆ, ਹੈਂਡਪੰਪ ਖਰਾਬ ਹੈ।",
            "as": "আমাৰ গাঁৱলৈ তিনি সপ্তাহ ধৰি খোৱা পানী অহা নাই, টিউবৱেলটো বেয়া হৈ গৈছে।",
            "en": "No drinking water has reached our village for three weeks; the handpump is broken.",
         }},
        {"urgency": 4, "summary": "No piped water for 20 days; dependent on tankers",
         "en": "Our ward has had no piped water supply for 20 days and we depend on private tankers.",
         "texts": {
            "hi": "हमारे मोहल्ले में 20 दिनों से नल का पानी नहीं आया, हम टैंकर पर निर्भर हैं।",
            "en": "Our ward has had no piped water supply for 20 days and we depend on private tankers.",
         }},
    ],
    "roads": [
        {"urgency": 4, "summary": "Village road broken; ambulances cannot reach in monsoon",
         "en": "The road to our village is broken and turns to mud in the rains; ambulances cannot reach us.",
         "texts": {
            "hi": "हमारे गाँव की सड़क टूटी हुई है और बारिश में कीचड़ बन जाती है, एम्बुलेंस नहीं पहुँच पाती।",
            "te": "మా ఊరి రోడ్డు పూర్తిగా దెబ్బతింది, వర్షాకాలంలో బురదగా మారుతుంది, అంబులెన్స్ రాలేకపోతోంది.",
            "ta": "எங்கள் ஊர் சாலை மிகவும் சேதமடைந்துள்ளது, மழைக்காலத்தில் சேறாகிறது, ஆம்புலன்ஸ் வர முடியவில்லை.",
            "kn": "ನಮ್ಮ ಊರಿನ ರಸ್ತೆ ಹಾಳಾಗಿದೆ, ಮಳೆಗಾಲದಲ್ಲಿ ಕೆಸರಾಗುತ್ತದೆ, ಆಂಬ್ಯುಲೆನ್ಸ್ ಬರಲು ಸಾಧ್ಯವಾಗುತ್ತಿಲ್ಲ.",
            "ml": "ഞങ്ങളുടെ നാട്ടിലേക്കുള്ള റോഡ് തകർന്നു, മഴക്കാലത്ത് ചെളിയാകുന്നു, ആംബുലൻസിന് എത്താൻ കഴിയുന്നില്ല.",
            "bn": "আমাদের গ্রামের রাস্তা ভাঙা, বর্ষায় কাদা হয়ে যায়, অ্যাম্বুলেন্স আসতে পারে না।",
            "mr": "आमच्या गावचा रस्ता खराब झाला आहे, पावसाळ्यात चिखल होतो, रुग्णवाहिका येऊ शकत नाही.",
            "gu": "અમારા ગામનો રસ્તો તૂટી ગયો છે, ચોમાસામાં કાદવ થઈ જાય છે, એમ્બ્યુલન્સ આવી શકતી નથી.",
            "or": "ଆମ ଗାଁର ରାସ୍ତା ଭାଙ୍ଗିଯାଇଛି, ବର୍ଷାରେ କାଦୁଅ ହୋଇଯାଏ, ଆମ୍ବୁଲାନ୍ସ ଆସିପାରୁନାହିଁ।",
            "pa": "ਸਾਡੇ ਪਿੰਡ ਦੀ ਸੜਕ ਟੁੱਟੀ ਹੋਈ ਹੈ, ਮੀਂਹ ਵਿੱਚ ਚਿੱਕੜ ਬਣ ਜਾਂਦੀ ਹੈ, ਐਂਬੂਲੈਂਸ ਨਹੀਂ ਪਹੁੰਚ ਸਕਦੀ।",
            "as": "আমাৰ গাঁৱৰ পথটো ভাঙি গৈছে, বাৰিষা বোকা হৈ যায়, এম্বুলেন্স আহিব নোৱাৰে।",
            "en": "The road to our village is broken and turns to mud in the rains; ambulances cannot reach us.",
         }},
        {"urgency": 4, "summary": "Large potholes on main road; two accidents this month",
         "en": "Huge potholes on the main road near the bus stand; two accidents happened this month.",
         "texts": {
            "hi": "बस स्टैंड के पास मुख्य सड़क पर बड़े गड्ढे हैं, इस महीने दो दुर्घटनाएँ हुईं।",
            "en": "Huge potholes on the main road near the bus stand; two accidents happened this month.",
         }},
    ],
    "health": [
        {"urgency": 4, "summary": "No doctor at PHC; 40 km travel for treatment",
         "en": "There is no doctor at our primary health centre; we have to travel 40 km for treatment.",
         "texts": {
            "hi": "हमारे प्राथमिक स्वास्थ्य केंद्र में कोई डॉक्टर नहीं है, इलाज के लिए 40 किलोमीटर जाना पड़ता है।",
            "te": "మా ప్రాథమిక ఆరోగ్య కేంద్రంలో డాక్టర్ లేరు, చికిత్స కోసం 40 కిలోమీటర్లు వెళ్ళాలి.",
            "ta": "எங்கள் ஆரம்ப சுகாதார நிலையத்தில் மருத்துவர் இல்லை, சிகிச்சைக்கு 40 கிலோமீட்டர் செல்ல வேண்டியுள்ளது.",
            "kn": "ನಮ್ಮ ಪ್ರಾಥಮಿಕ ಆರೋಗ್ಯ ಕೇಂದ್ರದಲ್ಲಿ ವೈದ್ಯರಿಲ್ಲ, ಚಿಕಿತ್ಸೆಗಾಗಿ 40 ಕಿಲೋಮೀಟರ್ ಹೋಗಬೇಕು.",
            "ml": "ഞങ്ങളുടെ പ്രാഥമിക ആരോഗ്യ കേന്ദ്രത്തിൽ ഡോക്ടർ ഇല്ല, ചികിത്സയ്ക്കായി 40 കിലോമീറ്റർ പോകണം.",
            "bn": "আমাদের প্রাথমিক স্বাস্থ্যকেন্দ্রে কোনো ডাক্তার নেই, চিকিৎসার জন্য ৪০ কিলোমিটার যেতে হয়।",
            "mr": "आमच्या प्राथमिक आरोग्य केंद्रात डॉक्टर नाहीत, उपचारासाठी 40 किलोमीटर जावे लागते.",
            "gu": "અમારા પ્રાથમિક આરોગ્ય કેન્દ્રમાં કોઈ ડૉક્ટર નથી, સારવાર માટે 40 કિલોમીટર જવું પડે છે.",
            "or": "ଆମ ପ୍ରାଥମିକ ସ୍ୱାସ୍ଥ୍ୟ କେନ୍ଦ୍ରରେ କୌଣସି ଡାକ୍ତର ନାହାଁନ୍ତି, ଚିକିତ୍ସା ପାଇଁ 40 କିଲୋମିଟର ଯିବାକୁ ପଡ଼େ।",
            "pa": "ਸਾਡੇ ਮੁੱਢਲੇ ਸਿਹਤ ਕੇਂਦਰ ਵਿੱਚ ਕੋਈ ਡਾਕਟਰ ਨਹੀਂ ਹੈ, ਇਲਾਜ ਲਈ 40 ਕਿਲੋਮੀਟਰ ਜਾਣਾ ਪੈਂਦਾ ਹੈ।",
            "as": "আমাৰ প্ৰাথমিক স্বাস্থ্য কেন্দ্ৰত কোনো চিকিৎসক নাই, চিকিৎসাৰ বাবে ৪০ কিলোমিটাৰ যাব লাগে।",
            "en": "There is no doctor at our primary health centre; we have to travel 40 km for treatment.",
         }},
        {"urgency": 3, "summary": "District hospital X-ray machine not working",
         "en": "The district hospital has no working X-ray machine and patients are sent to private labs.",
         "texts": {
            "hi": "जिला अस्पताल में एक्स-रे मशीन खराब है, मरीजों को निजी लैब भेजा जाता है।",
            "en": "The district hospital has no working X-ray machine and patients are sent to private labs.",
         }},
    ],
    "education": [
        {"urgency": 3, "summary": "School roof leaking; shortage of teachers",
         "en": "Our school building's roof leaks and there are not enough teachers.",
         "texts": {
            "hi": "हमारे स्कूल की छत टपकती है और शिक्षक भी पर्याप्त नहीं हैं।",
            "te": "మా పాఠశాల పైకప్పు కారుతోంది, ఉపాధ్యాయులు కూడా సరిపడా లేరు.",
            "ta": "எங்கள் பள்ளியின் கூரை ஒழுகுகிறது, போதுமான ஆசிரியர்களும் இல்லை.",
            "kn": "ನಮ್ಮ ಶಾಲೆಯ ಛಾವಣಿ ಸೋರುತ್ತಿದೆ, ಸಾಕಷ್ಟು ಶಿಕ್ಷಕರೂ ಇಲ್ಲ.",
            "ml": "ഞങ്ങളുടെ സ്കൂളിന്റെ മേൽക്കൂര ചോരുന്നു, ആവശ്യത്തിന് അധ്യാപകരുമില്ല.",
            "bn": "আমাদের স্কুলের ছাদ দিয়ে জল পড়ে, শিক্ষকও যথেষ্ট নেই।",
            "mr": "आमच्या शाळेचे छत गळते आणि पुरेसे शिक्षकही नाहीत.",
            "gu": "અમારી શાળાની છત ટપકે છે અને પૂરતા શિક્ષકો પણ નથી.",
            "or": "ଆମ ବିଦ୍ୟାଳୟର ଛାତ ଚୁଉଛି ଏବଂ ପର୍ଯ୍ୟାପ୍ତ ଶିକ୍ଷକ ମଧ୍ୟ ନାହାଁନ୍ତି।",
            "pa": "ਸਾਡੇ ਸਕੂਲ ਦੀ ਛੱਤ ਚੋਂਦੀ ਹੈ ਅਤੇ ਅਧਿਆਪਕ ਵੀ ਪੂਰੇ ਨਹੀਂ ਹਨ।",
            "as": "আমাৰ বিদ্যালয়ৰ চালখনৰ পৰা পানী সোমায়, পৰ্যাপ্ত শিক্ষকো নাই।",
            "en": "Our school building's roof leaks and there are not enough teachers.",
         }},
        {"urgency": 4, "summary": "180 students, 2 teachers; no girls' toilets",
         "en": "The government school has 180 students and only two teachers; there are no toilets for girls.",
         "texts": {
            "hi": "सरकारी स्कूल में 180 बच्चे हैं और सिर्फ दो शिक्षक, लड़कियों के लिए शौचालय नहीं है।",
            "en": "The government school has 180 students and only two teachers; there are no toilets for girls.",
         }},
    ],
    "power": [
        {"urgency": 3, "summary": "Few hours of power daily; transformer burnt for a month",
         "en": "We get electricity only a few hours a day; the transformer has been burnt for a month.",
         "texts": {
            "hi": "हमें दिन में केवल कुछ घंटे बिजली मिलती है, एक महीने से ट्रांसफार्मर जला हुआ है।",
            "te": "మాకు రోజుకు కొన్ని గంటలే కరెంటు వస్తుంది, నెల రోజులుగా ట్రాన్స్‌ఫార్మర్ కాలిపోయి ఉంది.",
            "ta": "எங்களுக்கு ஒரு நாளைக்கு சில மணி நேரம் மட்டுமே மின்சாரம் கிடைக்கிறது, ஒரு மாதமாக மின்மாற்றி எரிந்து கிடக்கிறது.",
            "kn": "ನಮಗೆ ದಿನಕ್ಕೆ ಕೆಲವೇ ಗಂಟೆ ವಿದ್ಯುತ್ ಸಿಗುತ್ತದೆ, ಒಂದು ತಿಂಗಳಿಂದ ಟ್ರಾನ್ಸ್‌ಫಾರ್ಮರ್ ಸುಟ್ಟುಹೋಗಿದೆ.",
            "ml": "ഞങ്ങൾക്ക് ദിവസം കുറച്ച് മണിക്കൂർ മാത്രമേ വൈദ്യുതി കിട്ടുന്നുള്ളൂ, ഒരു മാസമായി ട്രാൻസ്ഫോർമർ കത്തിപ്പോയിരിക്കുന്നു.",
            "bn": "আমরা দিনে মাত্র কয়েক ঘণ্টা বিদ্যুৎ পাই, এক মাস ধরে ট্রান্সফরমার পুড়ে আছে।",
            "mr": "आम्हाला दिवसातून फक्त काही तास वीज मिळते, महिनाभरापासून ट्रान्सफॉर्मर जळलेला आहे.",
            "gu": "અમને દિવસમાં માત્ર થોડા કલાક વીજળી મળે છે, એક મહિનાથી ટ્રાન્સફોર્મર બળી ગયું છે.",
            "or": "ଆମେ ଦିନକୁ କେବଳ କିଛି ଘଣ୍ଟା ବିଦ୍ୟୁତ ପାଉଛୁ, ଏକ ମାସ ହେଲା ଟ୍ରାନ୍ସଫର୍ମର ଜଳିଯାଇଛି।",
            "pa": "ਸਾਨੂੰ ਦਿਨ ਵਿੱਚ ਸਿਰਫ਼ ਕੁਝ ਘੰਟੇ ਬਿਜਲੀ ਮਿਲਦੀ ਹੈ, ਇੱਕ ਮਹੀਨੇ ਤੋਂ ਟ੍ਰਾਂਸਫਾਰਮਰ ਸੜਿਆ ਪਿਆ ਹੈ।",
            "as": "আমি দিনটোত মাত্ৰ কেইঘণ্টামান বিদ্যুৎ পাওঁ, এমাহ ধৰি ট্ৰান্সফৰ্মাৰটো জ্বলি আছে।",
            "en": "We get electricity only a few hours a day; the transformer has been burnt for a month.",
         }},
        {"urgency": 3, "summary": "6-8 hour daily power cuts hurting small businesses",
         "en": "Daily power cuts of 6-8 hours are shutting down small businesses in our area.",
         "texts": {
            "hi": "रोज़ 6-8 घंटे बिजली कटौती से छोटे दुकानदारों का काम ठप है।",
            "en": "Daily power cuts of 6-8 hours are shutting down small businesses in our area.",
         }},
    ],
    "sanitation": [
        {"urgency": 4, "summary": "Blocked drains, sewage on street; children falling sick",
         "en": "The drains are blocked and sewage is flowing on the street; children are falling sick.",
         "texts": {
            "hi": "नालियाँ जाम हैं और गंदा पानी सड़क पर बह रहा है, बच्चे बीमार पड़ रहे हैं।",
            "te": "మురుగు కాలువలు మూసుకుపోయాయి, మురుగునీరు వీధిలో ప్రవహిస్తోంది, పిల్లలు జబ్బు పడుతున్నారు.",
            "ta": "கழிவுநீர் கால்வாய்கள் அடைபட்டுள்ளன, கழிவுநீர் தெருவில் ஓடுகிறது, குழந்தைகள் நோய்வாய்ப்படுகிறார்கள்.",
            "kn": "ಚರಂಡಿಗಳು ಕಟ್ಟಿಕೊಂಡಿವೆ, ಕೊಳಚೆ ನೀರು ರಸ್ತೆಯಲ್ಲಿ ಹರಿಯುತ್ತಿದೆ, ಮಕ್ಕಳು ಕಾಯಿಲೆ ಬೀಳುತ್ತಿದ್ದಾರೆ.",
            "ml": "ഓടകൾ അടഞ്ഞിരിക്കുന്നു, മലിനജലം റോഡിലൂടെ ഒഴുകുന്നു, കുട്ടികൾക്ക് അസുഖം വരുന്നു.",
            "bn": "নর্দমা বন্ধ হয়ে গেছে, নোংরা জল রাস্তায় বইছে, শিশুরা অসুস্থ হয়ে পড়ছে।",
            "mr": "गटारे तुंबली आहेत, सांडपाणी रस्त्यावर वाहत आहे, मुले आजारी पडत आहेत.",
            "gu": "ગટરો ભરાઈ ગઈ છે, ગંદું પાણી રસ્તા પર વહે છે, બાળકો બીમાર પડે છે.",
            "or": "ନାଳ ବନ୍ଦ ହୋଇଯାଇଛି, ମଇଳା ପାଣି ରାସ୍ତାରେ ବହୁଛି, ପିଲାମାନେ ଅସୁସ୍ଥ ହେଉଛନ୍ତି।",
            "pa": "ਨਾਲੀਆਂ ਬੰਦ ਹਨ, ਗੰਦਾ ਪਾਣੀ ਗਲੀ ਵਿੱਚ ਵਗ ਰਿਹਾ ਹੈ, ਬੱਚੇ ਬਿਮਾਰ ਹੋ ਰਹੇ ਹਨ।",
            "as": "নলাবোৰ বন্ধ হৈ আছে, লেতেৰা পানী পথত বৈ আছে, শিশুবোৰ অসুস্থ হৈছে।",
            "en": "The drains are blocked and sewage is flowing on the street; children are falling sick.",
         }},
        {"urgency": 3, "summary": "Garbage uncollected for two weeks; mosquito breeding",
         "en": "Garbage has not been collected from our colony for two weeks; there are mosquitoes everywhere.",
         "texts": {
            "hi": "हमारी कॉलोनी से दो हफ्तों से कचरा नहीं उठाया गया, हर तरफ मच्छर हैं।",
            "en": "Garbage has not been collected from our colony for two weeks; there are mosquitoes everywhere.",
         }},
    ],
    "digital": [
        {"urgency": 2, "summary": "No mobile network or internet; students miss online classes",
         "en": "There is no mobile network or internet in our village; students cannot attend online classes.",
         "texts": {
            "hi": "हमारे गाँव में न मोबाइल नेटवर्क है न इंटरनेट, बच्चे ऑनलाइन पढ़ाई नहीं कर पाते।",
            "te": "మా గ్రామంలో మొబైల్ నెట్‌వర్క్, ఇంటర్నెట్ లేవు, విద్యార్థులు ఆన్‌లైన్ తరగతులకు హాజరు కాలేకపోతున్నారు.",
            "ta": "எங்கள் கிராமத்தில் மொபைல் நெட்வொர்க்கும் இணையமும் இல்லை, மாணவர்கள் ஆன்லைன் வகுப்புகளில் கலந்துகொள்ள முடியவில்லை.",
            "kn": "ನಮ್ಮ ಹಳ್ಳಿಯಲ್ಲಿ ಮೊಬೈಲ್ ನೆಟ್‌ವರ್ಕ್ ಮತ್ತು ಇಂಟರ್ನೆಟ್ ಇಲ್ಲ, ವಿದ್ಯಾರ್ಥಿಗಳು ಆನ್‌ಲೈನ್ ತರಗತಿಗಳಿಗೆ ಹಾಜರಾಗಲು ಆಗುತ್ತಿಲ್ಲ.",
            "ml": "ഞങ്ങളുടെ ഗ്രാമത്തിൽ മൊബൈൽ നെറ്റ്‌വർക്കും ഇന്റർനെറ്റും ഇല്ല, വിദ്യാർത്ഥികൾക്ക് ഓൺലൈൻ ക്ലാസുകളിൽ പങ്കെടുക്കാൻ കഴിയുന്നില്ല.",
            "bn": "আমাদের গ্রামে মোবাইল নেটওয়ার্ক বা ইন্টারনেট নেই, ছাত্রছাত্রীরা অনলাইন ক্লাস করতে পারে না।",
            "mr": "आमच्या गावात मोबाईल नेटवर्क किंवा इंटरनेट नाही, विद्यार्थी ऑनलाइन वर्गात सहभागी होऊ शकत नाहीत.",
            "gu": "અમારા ગામમાં મોબાઇલ નેટવર્ક કે ઇન્ટરનેટ નથી, વિદ્યાર્થીઓ ઓનલાઇન વર્ગોમાં જોડાઈ શકતા નથી.",
            "or": "ଆମ ଗାଁରେ ମୋବାଇଲ ନେଟୱର୍କ କି ଇଣ୍ଟରନେଟ ନାହିଁ, ଛାତ୍ରଛାତ୍ରୀମାନେ ଅନଲାଇନ କ୍ଲାସ କରିପାରୁନାହାଁନ୍ତି।",
            "pa": "ਸਾਡੇ ਪਿੰਡ ਵਿੱਚ ਨਾ ਮੋਬਾਈਲ ਨੈੱਟਵਰਕ ਹੈ ਨਾ ਇੰਟਰਨੈੱਟ, ਵਿਦਿਆਰਥੀ ਆਨਲਾਈਨ ਕਲਾਸਾਂ ਨਹੀਂ ਲਗਾ ਸਕਦੇ।",
            "as": "আমাৰ গাঁৱত মোবাইল নেটৱৰ্ক বা ইণ্টাৰনেট নাই, ছাত্ৰ-ছাত্ৰীয়ে অনলাইন শ্ৰেণী কৰিব নোৱাৰে।",
            "en": "There is no mobile network or internet in our village; students cannot attend online classes.",
         }},
        {"urgency": 2, "summary": "CSC closed; no BharatNet connection in panchayat",
         "en": "The common service centre is closed and there is no BharatNet connection in our panchayat.",
         "texts": {
            "hi": "कॉमन सर्विस सेंटर बंद है और हमारी पंचायत में भारतनेट कनेक्शन नहीं है।",
            "en": "The common service centre is closed and there is no BharatNet connection in our panchayat.",
         }},
    ],
}

ACK = {
    "hi": "आपका अनुरोध दर्ज कर लिया गया है। टिकट संख्या: {id}",
    "te": "మీ అభ్యర్థన నమోదు చేయబడింది. టికెట్ సంఖ్య: {id}",
    "ta": "உங்கள் கோரிக்கை பதிவு செய்யப்பட்டது. டிக்கெட் எண்: {id}",
    "kn": "ನಿಮ್ಮ ವಿನಂತಿಯನ್ನು ದಾಖಲಿಸಲಾಗಿದೆ. ಟಿಕೆಟ್ ಸಂಖ್ಯೆ: {id}",
    "ml": "നിങ്ങളുടെ അപേക്ഷ രജിസ്റ്റർ ചെയ്തു. ടിക്കറ്റ് നമ്പർ: {id}",
    "bn": "আপনার অনুরোধ নথিভুক্ত হয়েছে। টিকিট নম্বর: {id}",
    "mr": "तुमची विनंती नोंदवली गेली आहे. तिकीट क्रमांक: {id}",
    "gu": "તમારી વિનંતી નોંધાઈ ગઈ છે. ટિકિટ નંબર: {id}",
    "or": "ଆପଣଙ୍କ ଅନୁରୋଧ ପଞ୍ଜୀକୃତ ହୋଇଛି। ଟିକେଟ ନମ୍ବର: {id}",
    "pa": "ਤੁਹਾਡੀ ਬੇਨਤੀ ਦਰਜ ਕਰ ਲਈ ਗਈ ਹੈ। ਟਿਕਟ ਨੰਬਰ: {id}",
    "as": "আপোনাৰ অনুৰোধ পঞ্জীয়ন কৰা হৈছে। টিকেট নম্বৰ: {id}",
    "en": "Your request has been registered. Ticket number: {id}",
}

# Keywords for the offline analyser. Sanitation is checked before water so that
# "dirty water on the street" is not read as a drinking-water request.
KEYWORDS = {
    "sanitation": ["drain", "sewage", "garbage", "waste", "toilet", "mosquito", "नाली", "कचरा", "गटार", "सांडपाणी",
                   "మురుగు", "கழிவு", "ಚರಂಡಿ", "ಕೊಳಚೆ", "ഓട", "മലിന", "নর্দমা", "নলা", "ગટર", "ନାଳ", "ਨਾਲੀ"],
    "water": ["water", "tanker", "handpump", "borewell", "पानी", "पाणी", "नल", "నీరు", "నీళ్ళు", "குடிநீர்", "ನೀರು",
              "വെള്ളം", "জল", "পানী", "પાણી", "ପାଣି", "ਪਾਣੀ"],
    "roads": ["road", "pothole", "bridge", "सड़क", "गड्ढे", "रस्ता", "రోడ్డు", "சாலை", "ರಸ್ತೆ", "റോഡ്", "রাস্তা",
              "পথ", "રસ્તો", "ରାସ୍ତା", "ਸੜਕ"],
    "health": ["doctor", "hospital", "health", "clinic", "medicine", "डॉक्टर", "अस्पताल", "स्वास्थ्य", "आरोग्य", "డాక్టర్",
               "ఆరోగ్య", "மருத்துவ", "சுகாதார", "ವೈದ್ಯ", "ಆರೋಗ್ಯ", "ഡോക്ടർ", "ആരോഗ്യ", "ডাক্তার", "স্বাস্থ্য",
               "চিকিৎসক", "ડૉક્ટર", "આરોગ્ય", "ଡାକ୍ତର", "ସ୍ୱାସ୍ଥ୍ୟ", "ਡਾਕਟਰ", "ਸਿਹਤ"],
    "education": ["school", "teacher", "college", "स्कूल", "शिक्षक", "शाळ", "పాఠశాల", "ఉపాధ్యాయ", "பள்ளி",
                  "ஆசிரிய", "ಶಾಲೆ", "ಶಿಕ್ಷಕ", "സ്കൂൾ", "അധ്യാപക", "স্কুল", "শিক্ষক", "বিদ্যালয়", "શાળા", "શિક્ષક",
                  "ବିଦ୍ୟାଳୟ", "ଶିକ୍ଷକ", "ਸਕੂਲ", "ਅਧਿਆਪਕ"],
    "power": ["electricity", "power", "transformer", "बिजली", "वीज", "కరెంటు", "ட்ரான்ஸ்", "மின்", "ವಿದ್ಯುತ್",
              "വൈദ്യുതി", "বিদ্যুৎ", "વીજળી", "ବିଦ୍ୟୁତ", "ਬਿਜਲੀ", "ट्रांसफार्मर", "ट्रान्सफॉर्मर"],
    "digital": ["internet", "network", "mobile", "bharatnet", "wifi", "इंटरनेट", "नेटवर्क", "ఇంటర్నెట్", "இணைய",
                "ಇಂಟರ್ನೆಟ್", "ഇന്റർനെറ്റ്", "ইন্টারনেট", "ইণ্টাৰনেট", "ઇન્ટરનેટ", "ଇଣ୍ଟରନେଟ", "ਇੰਟਰਨੈੱਟ", "भारतनेट"],
}

URGENT_WORDS = ["urgent", "emergency", "death", "died", "accident", "flood", "fire", "sick", "तुरंत", "मौत",
                "बीमार", "దుర్ఘటన", "ఆపద", "அவசர", "ತುರ್ತು", "അടിയന്തര", "জরুরি"]


def detect_language(text: str) -> str:
    """Script-based language detection (offline fallback only)."""
    counts = {}
    for ch in text:
        cp = ord(ch)
        for lo, hi, code in ((0x0900, 0x097F, "hi"), (0x0980, 0x09FF, "bn"), (0x0A00, 0x0A7F, "pa"),
                             (0x0A80, 0x0AFF, "gu"), (0x0B00, 0x0B7F, "or"), (0x0B80, 0x0BFF, "ta"),
                             (0x0C00, 0x0C7F, "te"), (0x0C80, 0x0CFF, "kn"), (0x0D00, 0x0D7F, "ml"),
                             (0x0600, 0x06FF, "ur")):
            if lo <= cp <= hi:
                counts[code] = counts.get(code, 0) + 1
    if not counts:
        return "en"
    code = max(counts, key=counts.get)
    if code == "hi" and re.search(r"(आहे|नाही|आमच्या|आम्हाला)", text):
        return "mr"
    if code == "bn" and re.search("[ৰৱ]", text):  # ৰ ৱ are Assamese-only letters
        return "as"
    return code


def template_lookup():
    """Map every template sentence to (category, variant)."""
    out = {}
    for cat, variants in TEMPLATES.items():
        for v in variants:
            for text in v["texts"].values():
                out[text.strip()] = (cat, v)
    return out
