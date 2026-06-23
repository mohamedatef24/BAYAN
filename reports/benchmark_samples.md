# Benchmark Random Samples (30 per Dataset)

These are randomly selected samples exactly as stored in the JSON benchmark files.

## Spelling

```json
[
  {
    "id": "S007",
    "category": "hamza",
    "input": "هذا او ذاك لا فرق",
    "expected": "هذا أو ذاك لا فرق",
    "error_words": [
      "او"
    ],
    "severity": "major"
  },
  {
    "id": "S035",
    "category": "ta_marbuta",
    "input": "الحياه صعبه في المدينه",
    "expected": "الحياة صعبة في المدينة",
    "error_words": [
      "الحياه",
      "صعبه",
      "المدينه"
    ],
    "severity": "major"
  },
  {
    "id": "S012",
    "category": "hamza",
    "input": "اخيراً وصلنا إلى الهدف",
    "expected": "أخيراً وصلنا إلى الهدف",
    "error_words": [
      "اخيراً"
    ],
    "severity": "major"
  },
  {
    "id": "S053",
    "category": "alif_maqsura",
    "input": "بني المبنى الجديد",
    "expected": "بنى المبنى الجديد",
    "error_words": [
      "بني"
    ],
    "severity": "major"
  },
  {
    "id": "S079",
    "category": "multi_error",
    "input": "اين الجامعه الكبيره",
    "expected": "أين الجامعة الكبيرة",
    "error_words": [
      "اين",
      "الجامعه",
      "الكبيره"
    ],
    "severity": "critical"
  },
  {
    "id": "S014",
    "category": "hamza",
    "input": "انت طالب مجتهد",
    "expected": "أنت طالب مجتهد",
    "error_words": [
      "انت"
    ],
    "severity": "major"
  },
  {
    "id": "S005",
    "category": "hamza",
    "input": "اين ذهبت أمس",
    "expected": "أين ذهبت أمس",
    "error_words": [
      "اين"
    ],
    "severity": "major"
  },
  {
    "id": "S049",
    "category": "alif_maqsura",
    "input": "مصطفي طالب مجتهد",
    "expected": "مصطفى طالب مجتهد",
    "error_words": [
      "مصطفي"
    ],
    "severity": "major"
  },
  {
    "id": "S069",
    "category": "correct_text",
    "input": "الطالب المجتهد ينجح دائماً",
    "expected": "الطالب المجتهد ينجح دائماً",
    "error_words": [],
    "severity": "none"
  },
  {
    "id": "S043",
    "category": "ta_marbuta_prefix",
    "input": "فالسياره الجديده",
    "expected": "فالسيارة الجديدة",
    "error_words": [
      "فالسياره",
      "الجديده"
    ],
    "severity": "major"
  },
  {
    "id": "S044",
    "category": "ta_marbuta_prefix",
    "input": "كالمدرسه القديمه",
    "expected": "كالمدرسة القديمة",
    "error_words": [
      "كالمدرسه",
      "القديمه"
    ],
    "severity": "major"
  },
  {
    "id": "S080",
    "category": "multi_error",
    "input": "اول مره ازور المكتبه",
    "expected": "أول مرة أزور المكتبة",
    "error_words": [
      "اول",
      "مره",
      "ازور",
      "المكتبه"
    ],
    "severity": "critical"
  },
  {
    "id": "S021",
    "category": "hamza",
    "input": "اجمل مكان في العالم",
    "expected": "أجمل مكان في العالم",
    "error_words": [
      "اجمل"
    ],
    "severity": "major"
  },
  {
    "id": "S018",
    "category": "hamza",
    "input": "ارسل الرسالة فوراً",
    "expected": "أرسل الرسالة فوراً",
    "error_words": [
      "ارسل"
    ],
    "severity": "major"
  },
  {
    "id": "S070",
    "category": "correct_text",
    "input": "العلم نور والجهل ظلام",
    "expected": "العلم نور والجهل ظلام",
    "error_words": [],
    "severity": "none"
  },
  {
    "id": "S071",
    "category": "correct_text",
    "input": "أحب القراءة والكتابة",
    "expected": "أحب القراءة والكتابة",
    "error_words": [],
    "severity": "none"
  },
  {
    "id": "S032",
    "category": "ta_marbuta",
    "input": "الجامعه في القاهره",
    "expected": "الجامعة في القاهرة",
    "error_words": [
      "الجامعه",
      "القاهره"
    ],
    "severity": "major"
  },
  {
    "id": "S011",
    "category": "hamza",
    "input": "اطفال المدرسة يلعبون",
    "expected": "أطفال المدرسة يلعبون",
    "error_words": [
      "اطفال"
    ],
    "severity": "major"
  },
  {
    "id": "S001",
    "category": "hamza",
    "input": "انا طالب في الجامعة",
    "expected": "أنا طالب في الجامعة",
    "error_words": [
      "انا"
    ],
    "severity": "major"
  },
  {
    "id": "S058",
    "category": "word_split",
    "input": "رجع الىالبيت",
    "expected": "رجع إلى البيت",
    "error_words": [
      "الىالبيت"
    ],
    "severity": "major"
  },
  {
    "id": "S028",
    "category": "hamza_prefix",
    "input": "فالانسان يحتاج للعلم",
    "expected": "فالإنسان يحتاج للعلم",
    "error_words": [
      "فالانسان"
    ],
    "severity": "major"
  },
  {
    "id": "S050",
    "category": "alif_maqsura",
    "input": "موسي نبي عظيم",
    "expected": "موسى نبي عظيم",
    "error_words": [
      "موسي"
    ],
    "severity": "major"
  },
  {
    "id": "S006",
    "category": "hamza",
    "input": "اول مرة أزور هذا المكان",
    "expected": "أول مرة أزور هذا المكان",
    "error_words": [
      "اول"
    ],
    "severity": "major"
  },
  {
    "id": "S057",
    "category": "word_split",
    "input": "جلس عندالنافذة",
    "expected": "جلس عند النافذة",
    "error_words": [
      "عندالنافذة"
    ],
    "severity": "major"
  },
  {
    "id": "S039",
    "category": "ta_marbuta",
    "input": "الرحله طويله ومتعبه",
    "expected": "الرحلة طويلة ومتعبة",
    "error_words": [
      "الرحله",
      "طويله",
      "متعبه"
    ],
    "severity": "major"
  },
  {
    "id": "S025",
    "category": "hamza",
    "input": "اعتقد انه سيحضر غداً",
    "expected": "أعتقد أنه سيحضر غداً",
    "error_words": [
      "اعتقد",
      "انه"
    ],
    "severity": "major"
  },
  {
    "id": "S074",
    "category": "correct_text",
    "input": "الطقس جميل في الربيع",
    "expected": "الطقس جميل في الربيع",
    "error_words": [],
    "severity": "none"
  },
  {
    "id": "S062",
    "category": "correct_text",
    "input": "هذه المدرسة جميلة جداً",
    "expected": "هذه المدرسة جميلة جداً",
    "error_words": [],
    "severity": "none"
  },
  {
    "id": "S068",
    "category": "correct_text",
    "input": "هذا أو ذاك سواء عندي",
    "expected": "هذا أو ذاك سواء عندي",
    "error_words": [],
    "severity": "none"
  },
  {
    "id": "S047",
    "category": "alif_maqsura",
    "input": "المستشفي الكبير",
    "expected": "المستشفى الكبير",
    "error_words": [
      "المستشفي"
    ],
    "severity": "major"
  }
]
```

## Grammar

```json
[
  {
    "id": "G029",
    "category": "nasb",
    "input": "كي يتعلمون الدرس",
    "expected_fix": "يتعلموا",
    "error_words": [
      "يتعلمون"
    ],
    "severity": "major"
  },
  {
    "id": "G007",
    "category": "sv_agree",
    "input": "المعلمات حضر الاجتماع",
    "expected_fix": "حضرن",
    "error_words": [
      "حضر"
    ],
    "severity": "major"
  },
  {
    "id": "G003",
    "category": "sv_agree",
    "input": "المهندسون حضر الاجتماع",
    "expected_fix": "حضروا",
    "error_words": [
      "حضر"
    ],
    "severity": "major"
  },
  {
    "id": "G006",
    "category": "sv_agree",
    "input": "الأولاد لعب في الحديقة",
    "expected_fix": "لعبوا",
    "error_words": [
      "لعب"
    ],
    "severity": "major"
  },
  {
    "id": "G010",
    "category": "sv_agree",
    "input": "الطالبات كتب الواجب",
    "expected_fix": "كتبن",
    "error_words": [
      "كتب"
    ],
    "severity": "major"
  },
  {
    "id": "G009",
    "category": "sv_agree",
    "input": "العمال بنى المبنى",
    "expected_fix": "بنوا",
    "error_words": [
      "بنى"
    ],
    "severity": "major"
  },
  {
    "id": "G002",
    "category": "sv_agree",
    "input": "الطلاب يذهب إلى الجامعة",
    "expected_fix": "يذهبون",
    "error_words": [
      "يذهب"
    ],
    "severity": "major"
  },
  {
    "id": "G019",
    "category": "case",
    "input": "على العاملون في المصنع",
    "expected_fix": "العاملين",
    "error_words": [
      "العاملون"
    ],
    "severity": "major"
  },
  {
    "id": "G028",
    "category": "nasb",
    "input": "لم يفعلون الواجب بعد",
    "expected_fix": "يفعلوا",
    "error_words": [
      "يفعلون"
    ],
    "severity": "major"
  },
  {
    "id": "G031",
    "category": "correct",
    "input": "ذهب الطالب إلى المدرسة",
    "expected_fix": "",
    "error_words": [],
    "severity": "none"
  },
  {
    "id": "G017",
    "category": "case",
    "input": "من المعلمون الأكفاء",
    "expected_fix": "المعلمين",
    "error_words": [
      "المعلمون"
    ],
    "severity": "major"
  },
  {
    "id": "G036",
    "category": "correct",
    "input": "جاء المعلمون إلى الفصل",
    "expected_fix": "",
    "error_words": [],
    "severity": "none"
  },
  {
    "id": "G043",
    "category": "correct",
    "input": "إن العلم نافع للإنسان",
    "expected_fix": "",
    "error_words": [],
    "severity": "none"
  },
  {
    "id": "G020",
    "category": "case",
    "input": "عن المهندسون في الشركة",
    "expected_fix": "المهندسين",
    "error_words": [
      "المهندسون"
    ],
    "severity": "major"
  },
  {
    "id": "G011",
    "category": "gender",
    "input": "السيارة جميل جداً",
    "expected_fix": "جميلة",
    "error_words": [
      "جميل"
    ],
    "severity": "major"
  },
  {
    "id": "G035",
    "category": "correct",
    "input": "ذهبت البنات إلى المدرسة",
    "expected_fix": "",
    "error_words": [],
    "severity": "none"
  },
  {
    "id": "G026",
    "category": "dual",
    "input": "هاتان الطالبان مجتهدان",
    "expected_fix": "هذان",
    "error_words": [
      "هاتان"
    ],
    "severity": "major"
  },
  {
    "id": "G016",
    "category": "case",
    "input": "في المهندسون الماهرون",
    "expected_fix": "المهندسين",
    "error_words": [
      "المهندسون"
    ],
    "severity": "major"
  },
  {
    "id": "G044",
    "category": "correct",
    "input": "كان المطر غزيراً أمس",
    "expected_fix": "",
    "error_words": [],
    "severity": "none"
  },
  {
    "id": "G032",
    "category": "correct",
    "input": "كتبت الطالبة المقال بنجاح",
    "expected_fix": "",
    "error_words": [],
    "severity": "none"
  },
  {
    "id": "G021",
    "category": "five_nouns",
    "input": "إن أبوك رجل طيب جداً",
    "expected_fix": "أباك",
    "error_words": [
      "أبوك"
    ],
    "severity": "major"
  },
  {
    "id": "G030",
    "category": "nasb",
    "input": "حتى يعملون بجد",
    "expected_fix": "يعملوا",
    "error_words": [
      "يعملون"
    ],
    "severity": "major"
  },
  {
    "id": "G038",
    "category": "correct",
    "input": "يدرس الطالب في مكتبته",
    "expected_fix": "",
    "error_words": [],
    "severity": "none"
  },
  {
    "id": "G034",
    "category": "correct",
    "input": "أحب القراءة والكتابة كثيراً",
    "expected_fix": "",
    "error_words": [],
    "severity": "none"
  },
  {
    "id": "G001",
    "category": "sv_agree",
    "input": "البنات ذهب إلى المدرسة",
    "expected_fix": "ذهبن/ذهبت",
    "error_words": [
      "ذهب"
    ],
    "severity": "major"
  },
  {
    "id": "G013",
    "category": "gender",
    "input": "الطالبة متفوق في دراسته",
    "expected_fix": "متفوقة/دراستها",
    "error_words": [
      "متفوق",
      "دراسته"
    ],
    "severity": "major"
  },
  {
    "id": "G024",
    "category": "five_nouns",
    "input": "على أخوك أن يحضر",
    "expected_fix": "أخيك",
    "error_words": [
      "أخوك"
    ],
    "severity": "major"
  },
  {
    "id": "G014",
    "category": "gender",
    "input": "المدينة كبير وواسع",
    "expected_fix": "كبيرة وواسعة",
    "error_words": [
      "كبير",
      "وواسع"
    ],
    "severity": "major"
  },
  {
    "id": "G037",
    "category": "correct",
    "input": "ذهب الرجل إلى عمله",
    "expected_fix": "",
    "error_words": [],
    "severity": "none"
  },
  {
    "id": "G018",
    "category": "case",
    "input": "إلى المسافرون في المطار",
    "expected_fix": "المسافرين",
    "error_words": [
      "المسافرون"
    ],
    "severity": "major"
  }
]
```

## Punctuation

```json
[
  {
    "id": "P012",
    "category": "already_correct",
    "input": "كيف حالك؟ أنا بخير.",
    "should_add_punct": false,
    "severity": "major"
  },
  {
    "id": "P017",
    "category": "word_preservation",
    "input": "انا طالب في الجامعه",
    "expected_words_unchanged": true,
    "severity": "critical"
  },
  {
    "id": "P002",
    "category": "missing_question",
    "input": "هل أنت بخير يا صديقي",
    "should_add_punct": true,
    "severity": "minor"
  },
  {
    "id": "P006",
    "category": "missing_period",
    "input": "العلم نور والجهل ظلام والتعليم مهم",
    "should_add_punct": true,
    "severity": "minor"
  },
  {
    "id": "P003",
    "category": "missing_comma",
    "input": "مرحبا كيف حالك اليوم",
    "should_add_punct": true,
    "severity": "minor"
  },
  {
    "id": "P015",
    "category": "already_correct",
    "input": "ذهبت إلى المكتبة، واشتريت كتاباً.",
    "should_add_punct": false,
    "severity": "major"
  },
  {
    "id": "P008",
    "category": "missing_question",
    "input": "لماذا لم تحضر أمس",
    "should_add_punct": true,
    "severity": "minor"
  },
  {
    "id": "P011",
    "category": "already_correct",
    "input": "ذهبت إلى المدرسة. ثم عدت.",
    "should_add_punct": false,
    "severity": "major"
  },
  {
    "id": "P005",
    "category": "missing_period",
    "input": "هذا الكتاب مفيد جداً وأنصح بقراءته",
    "should_add_punct": true,
    "severity": "minor"
  },
  {
    "id": "P016",
    "category": "word_preservation",
    "input": "ذهبت الي المدرسه أمس",
    "expected_words_unchanged": true,
    "severity": "critical"
  },
  {
    "id": "P019",
    "category": "enumeration",
    "input": "أحتاج إلى خبز ولبن وجبن وبيض",
    "should_add_punct": true,
    "severity": "minor"
  },
  {
    "id": "P010",
    "category": "missing_multi",
    "input": "ذهبت إلى السوق واشتريت خبزاً ولحماً ثم عدت",
    "should_add_punct": true,
    "severity": "minor"
  },
  {
    "id": "P007",
    "category": "missing_question",
    "input": "ماذا تريد أن تفعل اليوم",
    "should_add_punct": true,
    "severity": "minor"
  },
  {
    "id": "P001",
    "category": "missing_period",
    "input": "ذهبت إلى المدرسة ثم عدت إلى البيت",
    "should_add_punct": true,
    "severity": "minor"
  },
  {
    "id": "P009",
    "category": "missing_comma",
    "input": "جاء أحمد ومحمد وعلي",
    "should_add_punct": true,
    "severity": "minor"
  },
  {
    "id": "P004",
    "category": "missing_multi",
    "input": "كيف حالك أنا بخير والحمد لله",
    "should_add_punct": true,
    "severity": "minor"
  },
  {
    "id": "P020",
    "category": "exclamation",
    "input": "يا إلهي هذا رائع جداً",
    "should_add_punct": true,
    "severity": "minor"
  },
  {
    "id": "P013",
    "category": "already_correct",
    "input": "أحمد، كيف حالك؟ هل أنت بخير؟",
    "should_add_punct": false,
    "severity": "major"
  },
  {
    "id": "P018",
    "category": "dialogue",
    "input": "قال أحمد أنا سعيد بلقائك يا صديقي",
    "should_add_punct": true,
    "severity": "minor"
  },
  {
    "id": "P014",
    "category": "already_correct",
    "input": "قال: أنا بخير، شكراً لك.",
    "should_add_punct": false,
    "severity": "major"
  }
]
```

## Entities

```json
[
  {
    "id": "E007",
    "category": "person",
    "input": "الأستاذ عمر بن الخطاب عادل",
    "entity": "عمر بن الخطاب",
    "severity": "major"
  },
  {
    "id": "E019",
    "category": "company",
    "input": "شركة OpenAI تطور الذكاء الاصطناعي",
    "entity": "OpenAI",
    "severity": "major"
  },
  {
    "id": "E003",
    "category": "person",
    "input": "عبد الرحمن أخي الأكبر",
    "entity": "عبد الرحمن",
    "severity": "major"
  },
  {
    "id": "E027",
    "category": "tech",
    "input": "منصة Node.js للخوادم",
    "entity": "Node.js",
    "severity": "major"
  },
  {
    "id": "E021",
    "category": "company",
    "input": "شركة Microsoft تنتج البرمجيات",
    "entity": "Microsoft",
    "severity": "major"
  },
  {
    "id": "E012",
    "category": "place",
    "input": "مدينة الرياض عاصمة المملكة",
    "entity": "الرياض",
    "severity": "major"
  },
  {
    "id": "E001",
    "category": "person",
    "input": "محمد صلاح لاعب كرة قدم مصري",
    "entity": "محمد صلاح",
    "severity": "major"
  },
  {
    "id": "E025",
    "category": "tech",
    "input": "إطار TensorFlow مفيد للتعلم",
    "entity": "TensorFlow",
    "severity": "major"
  },
  {
    "id": "E008",
    "category": "person",
    "input": "خالد بن الوليد قائد عظيم",
    "entity": "خالد بن الوليد",
    "severity": "major"
  },
  {
    "id": "E013",
    "category": "place",
    "input": "دبي مدينة عصرية وجميلة",
    "entity": "دبي",
    "severity": "major"
  },
  {
    "id": "E018",
    "category": "place",
    "input": "دمشق أقدم عاصمة في التاريخ",
    "entity": "دمشق",
    "severity": "major"
  },
  {
    "id": "E017",
    "category": "place",
    "input": "بغداد عاصمة العراق",
    "entity": "بغداد",
    "severity": "major"
  },
  {
    "id": "E002",
    "category": "person",
    "input": "عبدالله يدرس في الجامعة",
    "entity": "عبدالله",
    "severity": "major"
  },
  {
    "id": "E010",
    "category": "person",
    "input": "ابن سينا عالم عربي مشهور",
    "entity": "ابن سينا",
    "severity": "major"
  },
  {
    "id": "E016",
    "category": "place",
    "input": "المدينة المنورة طابة الطيبة",
    "entity": "المدينة المنورة",
    "severity": "major"
  },
  {
    "id": "E026",
    "category": "tech",
    "input": "مكتبة PyTorch للتعلم العميق",
    "entity": "PyTorch",
    "severity": "major"
  },
  {
    "id": "E011",
    "category": "place",
    "input": "جامعة القاهرة من أعرق الجامعات",
    "entity": "القاهرة",
    "severity": "major"
  },
  {
    "id": "E023",
    "category": "company",
    "input": "شركة Tesla للسيارات الكهربائية",
    "entity": "Tesla",
    "severity": "major"
  },
  {
    "id": "E004",
    "category": "person",
    "input": "أحمد محمود يعمل مهندساً",
    "entity": "أحمد محمود",
    "severity": "major"
  },
  {
    "id": "E009",
    "category": "person",
    "input": "صلاح الدين الأيوبي حرر القدس",
    "entity": "صلاح الدين الأيوبي",
    "severity": "major"
  },
  {
    "id": "E022",
    "category": "company",
    "input": "منصة GitHub للمطورين",
    "entity": "GitHub",
    "severity": "major"
  },
  {
    "id": "E028",
    "category": "tech",
    "input": "لغة JavaScript للويب",
    "entity": "JavaScript",
    "severity": "major"
  },
  {
    "id": "E014",
    "category": "place",
    "input": "القدس مدينة مقدسة عند المسلمين",
    "entity": "القدس",
    "severity": "major"
  },
  {
    "id": "E005",
    "category": "person",
    "input": "الدكتور حسن علي أستاذ جامعي",
    "entity": "حسن علي",
    "severity": "major"
  },
  {
    "id": "E015",
    "category": "place",
    "input": "مكة المكرمة أطهر البقاع",
    "entity": "مكة المكرمة",
    "severity": "major"
  },
  {
    "id": "E006",
    "category": "person",
    "input": "السيدة فاطمة الزهراء معلمة",
    "entity": "فاطمة الزهراء",
    "severity": "major"
  },
  {
    "id": "E030",
    "category": "tech",
    "input": "خدمة Docker للحاويات",
    "entity": "Docker",
    "severity": "major"
  },
  {
    "id": "E024",
    "category": "tech",
    "input": "أستخدم Python في البرمجة",
    "entity": "Python",
    "severity": "major"
  },
  {
    "id": "E029",
    "category": "tech",
    "input": "قاعدة بيانات MongoDB جيدة",
    "entity": "MongoDB",
    "severity": "major"
  },
  {
    "id": "E020",
    "category": "company",
    "input": "شركة Google عملاق التقنية",
    "entity": "Google",
    "severity": "major"
  }
]
```

## Religious

```json
[
  {
    "id": "R015",
    "category": "hadith",
    "input": "خيركم من تعلم القرآن وعلمه",
    "must_preserve": true,
    "severity": "critical"
  },
  {
    "id": "R007",
    "category": "falaq",
    "input": "قل أعوذ برب الفلق من شر ما خلق",
    "must_preserve": true,
    "severity": "critical"
  },
  {
    "id": "R001",
    "category": "basmalah",
    "input": "بسم الله الرحمن الرحيم",
    "must_preserve": true,
    "severity": "critical"
  },
  {
    "id": "R009",
    "category": "baqara",
    "input": "ذلك الكتاب لا ريب فيه هدى للمتقين",
    "must_preserve": true,
    "severity": "critical"
  },
  {
    "id": "R026",
    "category": "istighfar",
    "input": "أستغفر الله العظيم وأتوب إليه",
    "must_preserve": true,
    "severity": "critical"
  },
  {
    "id": "R012",
    "category": "shahada",
    "input": "لا إله إلا الله محمد رسول الله",
    "must_preserve": true,
    "severity": "critical"
  },
  {
    "id": "R022",
    "category": "dua",
    "input": "لا حول ولا قوة إلا بالله",
    "must_preserve": true,
    "severity": "critical"
  },
  {
    "id": "R027",
    "category": "takbir",
    "input": "الله أكبر الله أكبر لا إله إلا الله",
    "must_preserve": true,
    "severity": "critical"
  },
  {
    "id": "R014",
    "category": "hadith",
    "input": "إنما الأعمال بالنيات وإنما لكل امرئ ما نوى",
    "must_preserve": true,
    "severity": "critical"
  },
  {
    "id": "R021",
    "category": "dua",
    "input": "حسبنا الله ونعم الوكيل",
    "must_preserve": true,
    "severity": "critical"
  },
  {
    "id": "R024",
    "category": "tasbih",
    "input": "سبحان الله وبحمده سبحان الله العظيم",
    "must_preserve": true,
    "severity": "critical"
  },
  {
    "id": "R028",
    "category": "inna",
    "input": "إنا لله وإنا إليه راجعون",
    "must_preserve": true,
    "severity": "critical"
  },
  {
    "id": "R004",
    "category": "fatiha",
    "input": "اهدنا الصراط المستقيم صراط الذين أنعمت عليهم",
    "must_preserve": true,
    "severity": "critical"
  },
  {
    "id": "R003",
    "category": "fatiha",
    "input": "إياك نعبد وإياك نستعين",
    "must_preserve": true,
    "severity": "critical"
  },
  {
    "id": "R025",
    "category": "salawat",
    "input": "اللهم صل وسلم على نبينا محمد",
    "must_preserve": true,
    "severity": "critical"
  },
  {
    "id": "R016",
    "category": "hadith",
    "input": "المسلم من سلم المسلمون من لسانه ويده",
    "must_preserve": true,
    "severity": "critical"
  },
  {
    "id": "R002",
    "category": "fatiha",
    "input": "الحمد لله رب العالمين الرحمن الرحيم مالك يوم الدين",
    "must_preserve": true,
    "severity": "critical"
  },
  {
    "id": "R020",
    "category": "dua",
    "input": "رب اشرح لي صدري ويسر لي أمري",
    "must_preserve": true,
    "severity": "critical"
  },
  {
    "id": "R029",
    "category": "bismillah",
    "input": "بسم الله والحمد لله",
    "must_preserve": true,
    "severity": "critical"
  },
  {
    "id": "R019",
    "category": "dua",
    "input": "ربنا آتنا في الدنيا حسنة وفي الآخرة حسنة وقنا عذاب النار",
    "must_preserve": true,
    "severity": "critical"
  },
  {
    "id": "R023",
    "category": "hamdalah",
    "input": "الحمد لله رب العالمين",
    "must_preserve": true,
    "severity": "critical"
  },
  {
    "id": "R030",
    "category": "salam",
    "input": "السلام عليكم ورحمة الله وبركاته",
    "must_preserve": true,
    "severity": "critical"
  },
  {
    "id": "R013",
    "category": "shahada",
    "input": "أشهد أن لا إله إلا الله وأشهد أن محمداً رسول الله",
    "must_preserve": true,
    "severity": "critical"
  },
  {
    "id": "R005",
    "category": "ikhlas",
    "input": "قل هو الله أحد الله الصمد لم يلد ولم يولد",
    "must_preserve": true,
    "severity": "critical"
  },
  {
    "id": "R006",
    "category": "qadr",
    "input": "إنا أنزلناه في ليلة القدر",
    "must_preserve": true,
    "severity": "critical"
  },
  {
    "id": "R018",
    "category": "hadith",
    "input": "من كان يؤمن بالله واليوم الآخر فليقل خيراً أو ليصمت",
    "must_preserve": true,
    "severity": "critical"
  },
  {
    "id": "R011",
    "category": "kursi",
    "input": "الله لا إله إلا هو الحي القيوم لا تأخذه سنة ولا نوم",
    "must_preserve": true,
    "severity": "critical"
  },
  {
    "id": "R008",
    "category": "nas",
    "input": "قل أعوذ برب الناس ملك الناس إله الناس",
    "must_preserve": true,
    "severity": "critical"
  },
  {
    "id": "R017",
    "category": "hadith",
    "input": "لا يؤمن أحدكم حتى يحب لأخيه ما يحب لنفسه",
    "must_preserve": true,
    "severity": "critical"
  },
  {
    "id": "R010",
    "category": "baqara",
    "input": "الذين يؤمنون بالغيب ويقيمون الصلاة",
    "must_preserve": true,
    "severity": "critical"
  }
]
```

## Structured

```json
[
  {
    "id": "SC003",
    "category": "url",
    "input": "موقع http://localhost:8080/api جاهز",
    "protected": "http://localhost:8080/api",
    "severity": "critical"
  },
  {
    "id": "SC022",
    "category": "code",
    "input": "استخدم print('مرحبا') للطباعة",
    "protected": "print('مرحبا')",
    "severity": "critical"
  },
  {
    "id": "SC027",
    "category": "hashtag",
    "input": "مشروع #بيان رائع جداً",
    "protected": "#بيان",
    "severity": "major"
  },
  {
    "id": "SC023",
    "category": "code",
    "input": "المتغير const x = 5; في جافاسكريبت",
    "protected": "const x = 5;",
    "severity": "critical"
  },
  {
    "id": "SC001",
    "category": "url",
    "input": "زر الموقع https://example.com للمزيد",
    "protected": "https://example.com",
    "severity": "critical"
  },
  {
    "id": "SC021",
    "category": "measurement",
    "input": "الوزن 75kg",
    "protected": "75kg",
    "severity": "major"
  },
  {
    "id": "SC030",
    "category": "mention",
    "input": "تابع @bayan_app للتحديثات",
    "protected": "@bayan_app",
    "severity": "major"
  },
  {
    "id": "SC006",
    "category": "email",
    "input": "بريدي user.name@gmail.com للتواصل",
    "protected": "user.name@gmail.com",
    "severity": "critical"
  },
  {
    "id": "SC014",
    "category": "number",
    "input": "المسافة 25.5 كيلومتر",
    "protected": "25.5",
    "severity": "major"
  },
  {
    "id": "SC035",
    "category": "filepath",
    "input": "الملف في C:\\Users\\test\\file.txt",
    "protected": "C:\\Users\\test\\file.txt",
    "severity": "major"
  },
  {
    "id": "SC032",
    "category": "phone",
    "input": "الرقم +201012345678 متاح",
    "protected": "+201012345678",
    "severity": "major"
  },
  {
    "id": "SC034",
    "category": "version",
    "input": "الإصدار v2.1.0 متاح",
    "protected": "v2.1.0",
    "severity": "minor"
  },
  {
    "id": "SC005",
    "category": "email",
    "input": "أرسل لي على info@company.com",
    "protected": "info@company.com",
    "severity": "critical"
  },
  {
    "id": "SC012",
    "category": "time",
    "input": "الموعد الساعة 3:30 مساءً",
    "protected": "3:30",
    "severity": "major"
  },
  {
    "id": "SC008",
    "category": "date",
    "input": "تاريخ اليوم 15/06/2026",
    "protected": "15/06/2026",
    "severity": "major"
  },
  {
    "id": "SC026",
    "category": "json",
    "input": "البيانات {\"name\":\"Mohamed\"} صحيحة",
    "protected": "{\"name\":\"Mohamed\"}",
    "severity": "critical"
  },
  {
    "id": "SC002",
    "category": "url",
    "input": "الرابط https://www.google.com/search?q=test يعمل",
    "protected": "https://www.google.com/search?q=test",
    "severity": "critical"
  },
  {
    "id": "SC017",
    "category": "currency",
    "input": "الثمن 500$ أمريكي",
    "protected": "500$",
    "severity": "major"
  },
  {
    "id": "SC013",
    "category": "time",
    "input": "يبدأ الاجتماع 09:00 صباحاً",
    "protected": "09:00",
    "severity": "major"
  },
  {
    "id": "SC010",
    "category": "date",
    "input": "في تاريخ 01/01/2025 بدأنا",
    "protected": "01/01/2025",
    "severity": "major"
  },
  {
    "id": "SC020",
    "category": "measurement",
    "input": "المسافة 25km تقريباً",
    "protected": "25km",
    "severity": "major"
  },
  {
    "id": "SC011",
    "category": "time",
    "input": "الساعة 14:30 عصراً",
    "protected": "14:30",
    "severity": "major"
  },
  {
    "id": "SC018",
    "category": "currency",
    "input": "الميزانية 100 جنيه مصري",
    "protected": "100",
    "severity": "minor"
  },
  {
    "id": "SC025",
    "category": "sql",
    "input": "الاستعلام SELECT * FROM users يعمل",
    "protected": "SELECT * FROM users",
    "severity": "critical"
  },
  {
    "id": "SC007",
    "category": "email",
    "input": "تواصل عبر support@bayan.ai",
    "protected": "support@bayan.ai",
    "severity": "critical"
  },
  {
    "id": "SC028",
    "category": "hashtag",
    "input": "هاشتاق #الذكاء_الاصطناعي مهم",
    "protected": "#الذكاء_الاصطناعي",
    "severity": "major"
  },
  {
    "id": "SC015",
    "category": "number",
    "input": "السعر 1,000,000 جنيه",
    "protected": "1,000,000",
    "severity": "major"
  },
  {
    "id": "SC016",
    "category": "number",
    "input": "النسبة 95.7% من الطلاب نجحوا",
    "protected": "95.7%",
    "severity": "major"
  },
  {
    "id": "SC024",
    "category": "code",
    "input": "الدالة function test() {} تعمل",
    "protected": "function test() {}",
    "severity": "critical"
  },
  {
    "id": "SC031",
    "category": "phone",
    "input": "اتصل على 01012345678 للاستفسار",
    "protected": "01012345678",
    "severity": "major"
  }
]
```

## Hallucination

```json
[
  {
    "id": "H021",
    "category": "correct_simple",
    "input": "المعلم يشرح الدرس بوضوح.",
    "must_not_change": true,
    "severity": "major"
  },
  {
    "id": "H006",
    "category": "academic",
    "input": "تهدف هذه الدراسة إلى تحليل العوامل المؤثرة في جودة التعليم العالي.",
    "must_not_change": true,
    "severity": "major"
  },
  {
    "id": "H026",
    "category": "correct_compound",
    "input": "إن التعليم هو أساس تقدم الأمم، وبدونه لا يمكن تحقيق التنمية المستدامة.",
    "must_not_change": true,
    "severity": "major"
  },
  {
    "id": "H019",
    "category": "correct_simple",
    "input": "الطالب يدرس في المكتبة.",
    "must_not_change": true,
    "severity": "major"
  },
  {
    "id": "H013",
    "category": "technical",
    "input": "يستخدم النظام خوارزمية التعلم العميق لمعالجة اللغة الطبيعية.",
    "must_not_change": true,
    "severity": "major"
  },
  {
    "id": "H014",
    "category": "legal",
    "input": "وفقاً للمادة الخامسة من القانون المدني يحق للمتضرر المطالبة بالتعويض.",
    "must_not_change": true,
    "severity": "major"
  },
  {
    "id": "H002",
    "category": "news",
    "input": "شهدت المنطقة تطورات ميدانية متسارعة خلال الأيام الماضية.",
    "must_not_change": true,
    "severity": "major"
  },
  {
    "id": "H005",
    "category": "news",
    "input": "حققت الصادرات المصرية نمواً بنسبة عشرة بالمئة خلال الربع الأول.",
    "must_not_change": true,
    "severity": "major"
  },
  {
    "id": "H015",
    "category": "legal",
    "input": "يلتزم الطرف الأول بتسليم البضاعة خلال ثلاثين يوماً من تاريخ التعاقد.",
    "must_not_change": true,
    "severity": "major"
  },
  {
    "id": "H001",
    "category": "news",
    "input": "أعلن رئيس الوزراء عن خطة اقتصادية جديدة لتطوير البنية التحتية في البلاد.",
    "must_not_change": true,
    "severity": "major"
  },
  {
    "id": "H012",
    "category": "technical",
    "input": "تم تطوير التطبيق باستخدام إطار عمل حديث للواجهة الأمامية.",
    "must_not_change": true,
    "severity": "major"
  },
  {
    "id": "H022",
    "category": "correct_simple",
    "input": "نحن نحب بلادنا ونعمل من أجلها.",
    "must_not_change": true,
    "severity": "major"
  },
  {
    "id": "H027",
    "category": "correct_compound",
    "input": "تسعى الحكومة إلى تطوير منظومة التعليم وتحسين جودة المخرجات التعليمية.",
    "must_not_change": true,
    "severity": "major"
  },
  {
    "id": "H010",
    "category": "academic",
    "input": "يوصي الباحث بإجراء دراسات مستقبلية لتعميق الفهم.",
    "must_not_change": true,
    "severity": "major"
  },
  {
    "id": "H025",
    "category": "correct_simple",
    "input": "يجب أن نحترم الكبير ونعطف على الصغير.",
    "must_not_change": true,
    "severity": "major"
  },
  {
    "id": "H028",
    "category": "correct_compound",
    "input": "أثبتت الدراسات العلمية أن ممارسة الرياضة بانتظام تحسن الصحة النفسية والجسدية.",
    "must_not_change": true,
    "severity": "major"
  },
  {
    "id": "H018",
    "category": "literary",
    "input": "مضى الزمن سريعاً ولم يبق من الذكريات إلا ما حفظته القلوب.",
    "must_not_change": true,
    "severity": "major"
  },
  {
    "id": "H030",
    "category": "correct_compound",
    "input": "تلعب وسائل التواصل الاجتماعي دوراً مهماً في تشكيل الرأي العام المعاصر.",
    "must_not_change": true,
    "severity": "major"
  },
  {
    "id": "H003",
    "category": "news",
    "input": "أكد وزير التعليم أن المناهج الدراسية ستشهد تحديثاً شاملاً.",
    "must_not_change": true,
    "severity": "major"
  },
  {
    "id": "H009",
    "category": "academic",
    "input": "تم جمع البيانات من خلال استبانة إلكترونية وزعت على العينة.",
    "must_not_change": true,
    "severity": "major"
  },
  {
    "id": "H029",
    "category": "correct_compound",
    "input": "يعد الذكاء الاصطناعي من أهم التقنيات الحديثة التي ستغير مستقبل البشرية.",
    "must_not_change": true,
    "severity": "major"
  },
  {
    "id": "H011",
    "category": "technical",
    "input": "يعتمد النظام على بنية خادم عميل مع واجهة برمجة تطبيقات.",
    "must_not_change": true,
    "severity": "major"
  },
  {
    "id": "H020",
    "category": "correct_simple",
    "input": "ذهبت إلى السوق واشتريت خبزاً.",
    "must_not_change": true,
    "severity": "major"
  },
  {
    "id": "H008",
    "category": "academic",
    "input": "استخدم الباحثون المنهج الوصفي التحليلي لدراسة الظاهرة.",
    "must_not_change": true,
    "severity": "major"
  },
  {
    "id": "H023",
    "category": "correct_simple",
    "input": "القراءة تنمي العقل وتوسع المدارك.",
    "must_not_change": true,
    "severity": "major"
  },
  {
    "id": "H016",
    "category": "literary",
    "input": "كانت الشمس تغرب خلف الجبال وتلون السماء بألوان الذهب والأرجوان.",
    "must_not_change": true,
    "severity": "major"
  },
  {
    "id": "H007",
    "category": "academic",
    "input": "أشارت النتائج إلى وجود علاقة إيجابية بين المتغيرين المدروسين.",
    "must_not_change": true,
    "severity": "major"
  },
  {
    "id": "H017",
    "category": "literary",
    "input": "في تلك الليلة الهادئة كان صوت الأمواج يعزف لحناً حزيناً.",
    "must_not_change": true,
    "severity": "major"
  },
  {
    "id": "H024",
    "category": "correct_simple",
    "input": "الماء ضروري للحياة والصحة.",
    "must_not_change": true,
    "severity": "major"
  },
  {
    "id": "H004",
    "category": "news",
    "input": "افتتح الرئيس مشروعاً جديداً للطاقة المتجددة في الصحراء الغربية.",
    "must_not_change": true,
    "severity": "major"
  }
]
```

