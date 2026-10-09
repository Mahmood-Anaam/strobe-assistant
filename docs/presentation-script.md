# سيناريو عرض Strobe Assistant

هذا السيناريو مصمم لعرض مدته نحو 12–15 دقيقة لمسار Track A. نفّذ قسم التحضير قبل حضور المقيم، ولا تنشئ الموارد أثناء العرض.

## 1. التحضير قبل العرض

قبل العرض بيوم، تحقق من أن خدمتي ECS في حالة مستقرة، ثم ارفع صورة تجريبية وشغّل heartbeat مرة واحدة للتأكد من وجود سجل مستقل بتاريخ سابق للعرض.

```powershell
aws sts get-caller-identity
aws ecs describe-services --cluster n11553758-strobe-cluster --services n11553758-strobe-agent n11553758-strobe-mcp --region ap-southeast-2
aws events describe-rule --name n11553758-strobe-daily-heartbeat --region ap-southeast-2
```

جهّز مسبقًا:

- رابط ALB الخاص بواجهة ACP.
- صورة واضحة، مثل كلب أو شاطئ، باسم `demo-dog.jpg`.
- `userId` و`postId` حقيقيين من Assessment 1.
- تبويبات AWS مفتوحة على ECS، SQS، Lambda logs، DynamoDB، S3 Vectors، EventBridge وSecrets Manager.
- نافذة طرفية في جذر المشروع.

إذا بقي منع نماذج Bedrock التوليدية من سياسة المؤسسة، اعرض رسالة المنع نفسها باختصار واشرح fallback. لا تدّع أن التوليد نجح.

## 2. افتتاح العرض — دقيقة واحدة

قل:

> هذا المشروع هو Strobe Assistant لمسار A، وهو امتداد مباشر لخلفية Strobe التي سلّمتها في Assessment 1. يضيف بحثًا دلاليًا في صور المستخدم، وتصنيفًا غير متزامن للصور، ومحادثة عبر ACP، وتشغيلًا ذاتيًا مجدولًا. جميع الموارد في Sydney وتحمل student ID والوسمين المطلوبين.

افتح مخطط المعمارية في README ووضّح ثلاثة حدود رئيسية: وكيل ACP العام، خادم MCP الخاص والمنفصل، ووظائف Lambda الخلفية.

## 3. إثبات البنية السحابية — دقيقتان

في ECS اعرض:

1. cluster باسم `n11553758-strobe-cluster`؛
2. خدمة agent وخدمة MCP كلٌ على حدة؛
3. أن ALB يوجّه إلى agent فقط؛
4. أن MCP يستخدم internal ALB داخل VPC ولا يملك public load balancer.

قل:

> الفصل ليس شكليًا: وكيل ACP يستدعي MCP عبر واجهة موثقة، بينما MCP هو الذي يملك أدوات الوصول إلى DynamoDB وS3 Vectors وS3. مفتاح هذه الواجهة محفوظ في Secrets Manager ولا يوجد في الكود.

اعرض secret بالاسم والوسوم فقط، ولا تضغط Reveal secret value.

## 4. المسار غير المتزامن — ثلاث دقائق

اعرض أن عداد رسائل SQS يساوي صفرًا، ثم ارفع الصورة بمفتاح صحيح:

```powershell
aws s3 cp .\demo-dog.jpg s3://n11553758-strobe-media/<userId>/<postId>/demo-dog.jpg --content-type image/jpeg --region ap-southeast-2
```

اشرح التسلسل أثناء الانتظار:

> طلب الرفع ينتهي عند S3 ولا ينتظر الذكاء الاصطناعي. S3 يرسل Object Created إلى EventBridge، والقاعدة تضع الحدث في SQS، ثم Lambda تسحب الرسالة. هذا يفصل latency والتعطل عن واجهة الرفع ويسمح بالـretry وDLQ.

افتح CloudWatch logs لوظيفة classifier، ثم اعرض السجل الجديد:

```powershell
aws dynamodb scan --table-name n11553758-strobe-classifications --max-items 10 --region ap-southeast-2
```

أشر إلى `objectKey`, `labels`, `description`, `modelId`, `classifiedAt`, `userId` و`postId`. بعد ذلك افتح S3 Vectors وأثبت أن الفهرس ذو 1,024 بعدًا وCosine distance.

إذا ظهر `amazon-rekognition-detect-labels` في `modelId` فقل:

> حاول العامل استخدام Bedrock أولًا، لكن SCP في الحساب التعليمي رفض النموذج التوليدي. يحاول النظام Rekognition بعد ذلك؛ وفي هذا الحساب رُفضت الخدمة أيضًا، لذلك سُجل metadata fallback منخفض الثقة باسم مستقل، ثم أُنشئ الـembedding الحقيقي بواسطة Titan Text Embeddings في Bedrock. القيود ظاهرة في السجل وليست مخفية.

## 5. المحادثة والبحث الدلالي — ثلاث دقائق

افتح رابط ACP وأدخل user ID التجريبي بالطريقة المعدة في إعداد الخدمة، ثم اسأل بالإنجليزية لسهولة مقارنة labels:

> Find my photos of a dog and show me the best matches.

بيّن أن الرد يحتوي وصف النتائج وصورة موقعة inline. اشرح:

> هذا ليس keyword scan. MCP يستدعي Titan لإنشاء embedding للسؤال، ثم ينفذ nearest-neighbour query في S3 Vectors مع فلتر userId. روابط الصور presigned لمدة خمس دقائق، لذلك bucket لا يصبح عامًا.

أرسل صورة inline من زر الإرفاق واسأل:

> Use this image as context and find similar items in my library.

أشر إلى أن ACP يدعم الصور من المستخدم وإليه. إن كان التوليد ممنوعًا، بيّن أن الرد يعرض الأدلة المسترجعة بصورة صريحة بدل اختراع narrative؛ ثم وضّح أن نفس الكود يستخدم Nova Lite تلقائيًا عند رفع SCP.

## 6. أدوات MCP — دقيقة ونصف

اعرض `src/strobe_assistant/mcp_app.py` وسمِّ الأدوات:

- `search_photos`: بحث دلالي محكوم بالمستخدم؛
- `get_recent_posts`: سياق حديث من Strobe؛
- `get_agent_runs`: ذاكرة عمليات heartbeat.

قل:

> الأدوات صغيرة ومحددة الصلاحية؛ النموذج لا يحصل على وصول AWS عام. FastMCP يعرض بروتوكول MCP القياسي، ويوجد adapter HTTP خاص ومصادق عليه لوكيل ACP الحالي.

## 7. التشغيل الذاتي المجدول — دقيقة ونصف

افتح قاعدة EventBridge المسماة `n11553758-strobe-daily-heartbeat` واعرض الجدول والهدف. ثم اعرض جدول agent runs:

```powershell
aws dynamodb scan --table-name n11553758-strobe-agent-runs --max-items 10 --region ap-southeast-2
```

أشر إلى سجل timestamp يسبق وقت العرض وحقول `runType`, `summary`, `status`, و`sourceCount`.

قل:

> هذه ليست استجابة لطلب مستخدم؛ EventBridge شغّل Lambda ذاتيًا. السجل الدائم هو ذاكرة يمكن للوكيل قراءتها في التشغيل التالي. عند منع النموذج يسجل degraded بوضوح، وعند توفره ينتج retrospective grounded في التصنيفات.

## 8. الجودة والأمن — دقيقة واحدة

نفّذ أو اعرض نتيجة الأوامر التالية:

```powershell
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\pytest.exe
npm test
npm run build
```

قل:

> طبقت OOP وdependency injection لعزل Bedrock وrepository وvector store وworkflows، وهذا جعل الاختبارات لا تعتمد على الشبكة. النشر يدوي من خلال deployer موحد قابل لإعادة التشغيل.

## 9. الخاتمة — 30 ثانية

اختم بالنقاط التالية:

> الحل يحقق المتطلبات الثمانية: Bedrock، S3 Vectors، MCP منفصل، ACP مع صور بالاتجاهين، workflow غير متزامن، heartbeat مستقل، Secrets Manager، وECS. التصميم منخفض التكلفة وقابل للتوسع، ويحافظ على بيانات كل مستخدم عبر userId filter وروابط S3 قصيرة العمر.

## أسئلة متوقعة وإجابات مختصرة

**لماذا SQS بين EventBridge وLambda؟** لامتصاص الاندفاعات، retry مضبوط، DLQ، ومنع بطء التصنيف من التأثير في upload.

**لماذا لم تخزن vectors في DynamoDB؟** المتطلب هو S3 Vectors، وهو يقدم nearest-neighbour managed بدون تشغيل cluster، بينما DynamoDB يحتفظ بالبيانات التشغيلية القابلة للقراءة.

**كيف تمنع تسرب صور مستخدم لآخر؟** كل vector يحمل `userId`، وكل query يفرض filter عليه، وMCP يوقع URL بعد المطابقة فقط.

**ماذا يحدث إذا كرر S3 الحدث؟** معرف التصنيف deterministic مشتق من bucket/key، وكتابة vector تستخدم المفتاح نفسه، لذلك النتيجة upsert بدل إنشاء نسخ عشوائية.

**ماذا لو فشل العامل؟** SQS يعيد المحاولة؛ بعد الحد الأقصى تنقل الرسالة إلى DLQ، وتبقى الصورة الأصلية سليمة.

**لماذا خدمتان ECS؟** لإثبات فصل MCP عن الوكيل والواجهة، وتوسيع كل component بصورة مستقلة، وتقليل مساحة الوصول العامة.

**كيف تتعامل مع منع Bedrock؟** Titan embeddings متاح ويحقق retrieval الحقيقي. التوليد يمر عبر Bedrock فقط؛ عند رفض SCP لا أستخدم مزود LLM آخر، بل أسجل الحالة وأعيد دليل retrieval. تصنيف الصورة يحاول Rekognition ثم metadata fallback موسوم بوضوح إذا منعت السياسة الخدمتين.
