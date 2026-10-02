# 1 ~~.~~ Cloud ~~-n~~ ative API 

###### Table of Contents 

- ¢ <u>Overv</u> ~~<u>i</u>~~ <u>ew</u> 

- « ~~Unit Learning Outcomes assessed~~ 

- « <u>Attachments</u> 

- « ~~Understanding ‘Strobe’~~ 

   - <u>Preview</u> 

   - eo <u>Resources</u> 

   - <u>Entities of the data model</u> 

   - ~~Data objects~~ 

   - <u>Interface</u> 

   - <u>Strobe Web</u> 

   - © <u>Strobe API collection for Insomn</u> ~~<u>i</u>~~ <u>a</u> 

   - ~~Strobe Server JavaScript~~ 

   - ~~Strobe Server Python~~ 

- « ~~AWS~~ 

   - <u>Constraints</u> 

   - <u>Route 53</u> 

   - ° ~~S3~~ 

   - <u>Lambda</u> 

   - ° ~~Cognito~~ 

   - oe ~~DynamoDB~~ 

   - ~~API Gateway~~ 

   - ~~Certificate Manager~~ 

- « ~~What you need to do~~ 

   - ~~User Story 1: Secure Public Access (3 marks)~~ 

   - ~~User Story 2: Meaningful Domain Access (3 marks)~~ 

   - ~~User Story 3: User Registration (3 marks)~~ 

   - ~~User Story 4: Authentication (3 marks)~~ 

   - ~~User Story 5: Authorization & Account Management (3 marks)~~ 

   - ~~User Story 6: Create Content (3 marks)~~ 

   - ~~User Story 7: Secure Image Upload (3 marks)~~ 

   - ~~User Story 8: Content Retrieval (3 marks)~~ 

   - ~~User Story 9: Secure Data Storage Design (3 marks)~~ 

   - ~~User Story 10: End-to-End Integration (3 marks)~~ 

- « ~~Submit YAML to Gradescope~~ 

   - ~~Sample YAML~~ 

      - <mark>=</mark> ~~submission-infra.yml~~ 

      - = ~~submission-routes.yml~~ 

   - ~~YAML in depth~~ 

¢ <u>Submi</u> ~~<u>s</u>~~ <u>s</u> ~~<u>i</u>~~ <u>on</u> « <u>Feedback</u> 

¢ <u>Moderation</u> 

###### <u>e</u> ~~<u>Change lo</u>~~ <u>g</u> 

###### Overview 

You will implement an HTTP API using cloud ~~-n~~ ative technologies such as serverless functions and managed databases. 

Strobe is a social media platform where people share photos with their friends ~~.~~ It started as a side project, unexpectedly blew up, and now has millions of active users ~~.~~ The problem is that the backend was built to get the app out the door, not to support a platform at this scale ~~.~~ 

Today, everything runs on a single virtual machine in the cloud ~~.~~ When user numbers spike, the lonely platform engineer scrambles to launch a bigger machine with more CPU and memory, then redirects tarffic across to it. An upgrade means there will be an outage while the new server comes online and a poor response from users that are impacted by that. During busy periods, the server struggles to keep up and users are left waiting for the app to respond. During quieter parts of the day, that same oversized server sits mostly idle, burning through the company's budget ~~.~~ 

This is not sustainable ~~.~~ The monolithic server is not serving its purpose so you have been brought you in to fix all the problems ~~.~~ The only solution is to use a serverless cloud architecture ~~.~~ 

Strobe has provided you with the backend source code, together with a web application and an Insomnia collection for user acceptance testing ~~.~~ Your task is to modernise the infrastructure by replacing the monolithic server with a serverless cloud architecture that can automatically scale to demand, tolerate failures, and reduce operating costs, all while preserving the existing API so the frontend continues to work without modification ~~.~~ 

You will need to think carefully about how each part of the app translates to a serverless architecture. Every component of the existing system has a cloud ~~-n~~ ative equivalent. For example, uploaded photos should no longer live on the local SSD of a virtual machine, but in Amazon S3 ~~.~~ User authentication should move from the custom implementation to Amazon Cognito ~~.~~ Instead of exposing the application directly to the internet, incoming HTTP requests should be handled by API Gateway ~~.~~ Structured data currently stored in ~~LowDB~~ & ~~(https://github.com/typicode/l~~ owdb)should be migrated to DynamoDB ~~.~~ Rather than a long ~~-~~ running Python or Node.js process handling every request, the application's logic should be broken into AWS Lambda functions that execute only when needed. 

This assessment <u>item is</u> eligible for the 48 hour extension ~~.~~ You can read more <u>information</u> about this on the ~~HiQ website (https://qutvirtual4.qut.edu.au/group/student/study/assignments/submitting/lateassignments-and-extensions).~~ 

### Unit Learning Outcomes assessed 

- ¢ ULO2 Design and implement scalable cloud applications using industry standard languages and APIs, deployed on a public cloud infrastructure and leveraging a range of cloud services ~~.~~ 

<u>30% of final grade</u> 

<u>Individual</u> 

<u>Grade out of 30</u> 

###### Attachments 

- ¢ Strobe Web v1 ~~.0.0: CAB432-Strobe-Web-1.0.0.zip (https://canvas.qut.edu.au/courses/23778/files/8972231/download)~~ 

- ¢ Strobe Server Js v1.0.0 ~~<u>:</u> CAB432-Strobe-Server-Js-1.0.0.zip (https://canvas.qut.edu.au/courses/23778/files/8972232/download)~~ 

- ¢ Strobe Server Py v1 ~~.0~~ .0 ~~<u>:</u> CAB432-Strobe-Server-Py-1.0.0.zip~~ 

   - ~~(https://canvas.qut.edu.au/courses/23778/files/8972233/download)~~ 

- ¢ Template of infrastructure YAML ~~: submission-infra.yml~~ 

   - ~~(https://canvas.qut.edu.au/courses/23778/files/8973269/download)~~ 

- « Template of routes YAML ~~: submission-routes.yml (https://canvas.qut.edu.au/courses/23778/files/8972235/download)~~ 

#### UnderstandingH ' 'Strobe ' 

Strobe is a platform for sharing photos with family and friends ~~.~~ You may notice similarities to popular social media platforms. Below are screenshots and the technical information about the app ~~.~~ 

Strobe was implemented as a decoupled stack containing ~~:~~ a server app and a web app ~~.~~ They interact by exchanging JSON via HTTP: ~~i.~~ e ~~.,~~ a modern API ~~.~~ 

We encourage that rather than relying solely on the documentation, you inspect and understand the codebase yourself, particularly the source code of the server app ~~.~~ Eventually you will need to refactor it to be compatible with an AWS serverless stack ~~.~~ 

The web app is not important ~~.~~ It is provided it to you only so you can test your implementation of your cloud ~~-~~ native server, and so that you have a GUI to work with ~~.~~ There is also a "collection" for ~~Insomnia~~ = ~~(https://insomnia.rest/download).~~ 

Keep in mind that CAB432 is not primarily a software development unit ~~.~~ Its focus is on cloud computing and cloud ~~-n~~ ative application deployment ~~.~~ Accordingly, the application code is provided so that you can concentrate on designing and deploying a serverless cloud architecture rather than building the application from scratch. 

We provide both JavaScript and Python implementations of the server ~~-~~ side HTTP API, allowing you to choose your preferred language. The client application is implemented in React and communicates with your deployed API over HTTP. 

Your task is entirely on the cloud/backend side ~~:~~ design, provision, and secure the AWS infrastructure and backend integration needed to make the provided frontend fully functional against your own deployment ~~.~~ You are not assessed on frontend code: only on the backend API contract and the cloud architecture behind it ~~.~~ 

The features of Strobe Server are complete and should not be modified, removed and no new features added ~~.~~ 

###### Preview 

Users of Strobe must be authenticated 



<!-- Start of picture text -->
Welcome back. Log in to continue<br>sharing moments<br>Password<br><!-- End of picture text -->

Strobe has a home page, with a feed and moments banner ~~.~~ 

Strobe 

Q 



<!-- Start of picture text -->
tw)<br><!-- End of picture text -->



<!-- Start of picture text -->
, Following<br>Stories Archive<br>a XH —— rc) Claudia_Heathcote@y... Unfollow<br>ra, an<br>Add story ‘ 7<br>@Earmest73.. @Taya.Spor Your story  @Claudia. to ) Miguel35@hotmailcom Unfollow<br>e Earnest73@yahoo.com —_Unfollow<br>@ Taya.Sporer63@yahoo.com : ) Taya.Sporer63@yahoo.... Unfollow<br>Antiquus capio eaque callide talus tenuis calamitas.<br>a, S SS? - r} Followers<br>® ~ Sg NS *<br>&~ F - altsaS ag? @ < @ Taya.Sporer63@yahoo.com<br>SS Ss ;<br>j sd _ e Earnest73@yahoo.com<br>y<br>. ail AGRE | er. . R<br>Moments open over the page content<br>tr BreS@yahoo.com 16/07/2026 §<br>4<br>Dam Sulum quae CUpiditate contigo compello<br><!-- End of picture text -->

Each user has their own profile 

Q 

##### Strobe 



<!-- Start of picture text -->
tw)<br><!-- End of picture text -->



<!-- Start of picture text -->
Wendy.Wisoky@yahoo.com<br><!-- End of picture text -->



<!-- Start of picture text -->
Wendy.Wisoky@yahoo.com<br>3 2 4<br>Posts Followers Following<br>| ae ) i AG Bik: ate<br>4 ¢ " A Re e se WteG SeraBe Ba! | a sillsi “4<br>2<br>tT: + Pescae = apsme a ae.b See—_— esSis<br>Posts can be created with up to five photographs<br>Strobe Q tw)<br>Stories Archive Followingit<br>lalso like dogs! idia_Heathcote@y.. Unfollow<br>COBEN) | Siete | uel35@hotmail.com Unfollow<br>1/5 selected Remove all<br>| B Dog_Breeds.jpg yest73@yahoo.com —_Unfollow<br>rw) Miguel3S5@hotmail.com A, EE<br>a.Sporer63@yahoo... Unfollow<br>Subito creator articulus pecto p (B3Photo or Video F share]<br>T "Followers<br>©@ 4 likes-1comments @ Taya.Sporer63@yahoo.com<br>rr) Taya.Sporer63@yahoo.com | mont) 200 é e Earnest73@yahoo.com<br>Antiquus capio eaque callide talus tenuis calamitas.<br><!-- End of picture text -->

Comments can be added to a post 



<!-- Start of picture text -->
Strobe Q ra]<br>rw} Wendy.Wisoky@yahoo.com x<br>Wendy.Wisoky@yahoo.com| also like dogs! d<br>6 Angelo.Kuvalis@hotmail.com so dol @ \<br>}<br>>, Delete we<br>< aia ><br>&<br>i" fat AN<br>Add acomment<br><!-- End of picture text -->

###### Resources 

We have provided the server app in your choice of either JavaScript or Python ~~.~~ You are expected to migrate this backend to AWS to meet the user stories and acceptance criteria ~~.~~ 

The features of Strobe Server are complete and their behaviours should not be modified, removed or new features added. 

The application programming interface (API) must remain unchanged ~~.~~ Otherwise, the autograder will be unable to assess your submission ~~.~~ While the implementation behind the interface may change, the interface itself must remain the same. 

We have also provided a web app that, by default, communicates to a server running at http://localhost:3eee ~~.~~ This can be changed to point to your deployed backend once you have it running ~~.~~ The frontend is not part of the assessment, but you may use it to test your server (local or cloud) ~~.~~ 



<!-- Start of picture text -->
©<br><!-- End of picture text -->

Profile 

Set API URL Delete account 

Log out 

Welcome back. Log in to continue sharing moments. Email Password ® 

Don't have an account? Sign up CONNECTED API http: //localhost : 3000 env/default Change API URL 

###### Entities of the data model 

There are six entities in the model ~~:~~ User, Post, Comment, Like, Follow and Moment ~~.~~ 

The relationships between the entities are as follows: 

User to Post (1 ~~:~~ M) ~~:~~ A user can create many posts, but each post is created by exactly one user ~~.~~ 

User to Comment (1 ~~<u>:</u>~~ M) ~~:~~ A user can write many comments, but each comment is authored by exactly one user ~~.~~ 

Post to Comment (1 ~~:~~ M) ~~:~~ A post can have many comments, but each comment belongs to exactly one post ~~.~~ User to Like (1 ~~:~~ M) ~~:~~ A user can like many posts, but each like is made by exactly one user ~~.~~ 

Post to Like (1 ~~:~~ M) ~~:~~ A post can receive many likes, but each like refers to exactly one post ~~.~~ 

User to Follow (1 ~~:~~ M) ~~:~~ The Follow entity models a sel ~~f-~~ referencing many ~~-to-~~ many relationship between users. A user can follow many other users and can also be followed by many users. Each follow record contains a followerId and a followeeid , both of which reference the User entity ~~.~~ 

User to Moment (1 ~~:~~ M) ~~:~~ A user can create many moments, but each moment belongs to exactly one user ~~.~~ The User entity is central to the model, with one ~~-~~ t ~~o-~~ many relationships to Post, Comment, Like, and Moment, and a recursive many ~~-to-~~ many relationship with itself through Follow ~~.~~ The Post entity is also central, having one ~~-~~ t ~~o-~~ many relationships with both Comment and Like ~~.~~ 

###### Data objects 

« Users 

{ "id": "@2092163 ~~-~~ 04fb ~~-~~ 4766 ~~-~~ a823 ~~-~~ cd161891db21", “username”: "Wendy.Wisoky@yahoo.com", “email”: “Wendy.Wisoky@yahoo.com", "password": "$2b$10$w.9T/w.DX@@010LmmLXYp.AhsLADBpjWn8gS4XNLAxJaoIl1D3QswO", "pole": "moderator", "“createdAt": "2@26 ~~-~~ 02 ~~-~~ 18T11:35:18.962Z", “updatedAt": "2@26 ~~-~~ @7 ~~-~~ 16T07:04:14.240Z" } 

¢ Posts 

{ “id": "29e9cab ~~b-~~ 785 ~~7-~~ 403 ~~c-~~ 8bc ~~c-~~ 85eled5c6dbb", “userId": "@2092163 ~~-~~ 04fb ~~-~~ 4766 ~~-~~ a823 ~~-~~ cd161891db21", "title": "This is my pet cat Foo.", "description": "Foo bar baz long description.", "images": [ 1, "http: //localhost : 3000/uploads/@2092163/906a58cf/133a3272.jpg" 

"status": "active", “createdAt": "2026 ~~-~~ 01 ~~-~~ 30T21:21:26.836Z", “updatedAt": "2026 ~~-~~ @7 ~~-~~ 16T07:04:14.365Z" 

} 

###### « Comments 

- { “id": “62d167ac ~~-~~ dfc2 ~~-~~ 4858 ~~-~~ a645 ~~-2~~ 23e3c8eb177", “postId": "29e9cabb ~~-~~ 785 ~~7-~~ 403 ~~c-~~ 8bc ~~c-~~ 85eled5cédbb", “userId": "@be8deeb ~~-~~ 81eb ~~-~~ 427f ~~-~~ be26 ~~-~~ 58054db27f6b", “text": "Foo is cute!", “createdAt": “2025 ~~-~~ 12 ~~-~~ 26T23:11:20.081Z", “updatedAt": "2026 ~~-~~ @7 ~~-~~ 16T07:04:14.370Z" 

- } 

« Likes 

{ "id": "@6df53f8 ~~-~~ 1b4c ~~-~~ 4397 ~~-~~ b4e5 ~~-~~ d26db3a5e2be", “postId": "29e9cabb ~~-~~ 7857 ~~-~~ 403c ~~-~~ 8bcc ~~-~~ 85e1ed5c6dbb", “userId": "@be8dee ~~b-~~ 81e ~~b-~~ 427 ~~f-~~ be2 ~~6-~~ 58054db27f6b", “createdAt": "2026 ~~-~~ 01 ~~-~~ 15T20:03:39.329Z" } 

« Follows 

{ "id": "650927f6 ~~-~~ c6a2 ~~-~~ 41fc ~~-~~ 96c8 ~~-f~~ ac602dc7ael", “followerId": "@2092163 ~~-~~ 04fb ~~-~~ 4766 ~~-~~ a823 ~~-~~ cd161891db21", “followeeId": “a216e737 ~~-~~ 76e9 ~~-~~ 47d8 ~~-~~ a39f ~~-~~ a2efce8cdfab", “createdAt": "2@25 ~~-~~ 12 ~~-~~ 03T01:40: 38.5122" } 

« Moments 

{ “id": "4e1729a6 ~~-~~ 3f2e ~~-~~ 4cf1 ~~-~~ a48b ~~-~~ 566db443b077", “userId": "@2092163 ~~-~~ 04fb ~~-~~ 4766 ~~-~~ a823 ~~-~~ cd161891db21", “imageUr1": “caption": “Numquam“https: //loremflickr.com/640/480?1locvorax arcesso claudeo corrigo ~~k=~~ quos8335821904019456"sumptus.", , "status": "active", “createdAt": "2026 ~~-~~ @7 ~~-~~ 16T01:27:29.764Z", “expiresAt": "2026 ~~-~~ 07 ~~-~~ 17T01:27:29.764Z", “updatedAt": "2026 ~~-~~ @7 ~~-~~ 16T07:04:14.373Z" } 

###### Interface 

Strobe's only interface is built on HTTP and follows a REST- ~~l~~ ike design ~~.~~ 

|/v1/auth/register|POST_||auth|Register user|
|---|---|---|---|
|/v1/auth/login|POST_||auth|Login as existing user|
|/v1/posts/user/{userId}<br>||post<br>|Get posts for user<br>|
|~~/V1/posts/{id}~~<br>|~~[GET~~<br>~~[~~<br><br>|~~post~~<br>|~~GetpostbyID~~<br>|
|~~/v1/posts/{id}~~|~~PUT~~<br>~~[~~|~~post~~|<br>~~UpdatepostbyID~~|
|/v1/posts/{id}|DELETE||post|<br>Delete post by ID|
|/v1/posts/{id}/like|POST|_|post|Like a post|
|/v1/posts/{id}/like|DELETE||post|Unlikeapost|



|~~|~~<br>~~Route~~|~~Method ~~|~~[Controller~~|~~]~~<br>~~Action~~|
|---|---|---|---|





###### Strobe Web 

To use Strobe Web, after downloading and decompressing, run ~~<u>:</u>~~ 

- $ npm install 

- added 154 packages, and audited 155 packages in 45s 

- 15 packages are looking for funding run “npm fund’ for details 

- 5 vulnerabilities (1 moderate, 4 high) 

- To address issues that do not require attention, run: npm audit fix 

- To address all issues (including breaking changes), run: npm audit fix ~~--~~ force 

- Run “npm audit’ for details. 

then 

- $ npm run dev 

- strobe ~~-~~ client@1.0.0 dev 

- > vite 

VITE v5.4.21 ready in 2562 ms 

> Local: http://localhost:5173/ > Network: use ~~--~~ host to expose > press h + enter to show help 

###### Strobe API collection for Insomnia 

The collection is provided in the source code of the server apps aS <server>/insomnia/strobe ~~-~~ openapi.yaml 



<!-- Start of picture text -->
QQ ——.- Q seach 7 ee<br>Projects (2) & x OS] Loginuser X = +<br>|W strobe toca a1 1.00 s . .<br>s ‘ .<br>ke. bradford@example.com’ Unauthorised”,<br>=<br>=<br>=<br>=<br>=<br><!-- End of picture text -->

Strobe Server JavaScript If you use Strobe Sever JavaScript as a basis for your assignment then do not also use Strobe Server Python. 

To run the JavaScript (Node. ~~j~~ s) version of Strobe Server ~~<u>:</u>~~ 

$ npm install 

added 253 packages, and audited 254 packages in 55s 

55 packages are looking for funding run “npm fund” for details 

1 moderate severity vulnerability 

To address all issues (including breaking changes), run: npm audit fix ~~--~~ force Run ‘npm audit for details. 

$ npm run seed 

> strobe ~~-~~ server@1.0.0 seed > node src/scripts/seed.js Seeding database... 

Generating users... 10 users created Generating posts... 3@ posts created Generating follows... 32 follow relationships created Generating likes... 74 likes created Generating comments... 73 comments created Generating moments... 18 moments created 

Database seeded successfully. 

Sample credentials: 1. Email: Wendy.Wisoky@yahoo.com, Password: password123, Role: moderator 2. Email: Angelo.Kuvalis@hotmail.com, Password: password123, Role: user 3. Email: Claudia ~~H~~ eathcote@yahoo.com, Password: password123, Role: user 

$ npm run dev 

> strobe ~~-~~ server@1.0.0 dev > nodemon ~~--~~ watch src ~~--~~ ext js,mjs,cjs,json src/index.js [nodemon] 3.1.14 [nodemon] to restart at any time, enter “rs [nodemon] watching path(s): src\**\* [nodemon] watching extensions: js,mjs,cjs,json [nodemon] starting “node src/index.js~ Server is now running at http://localhost:3000 

###### Strobe Server Python 

If you use Strobe Sever Python as a basis for your assignment then do not also use Strobe Server JavaScript. 

To run the Python version of Strobe Server: 

$ py ~~-~~ 3.14 ~~-~~ m pip install ~~-~~ r requirements.txt Collecting ... Successfully installed ... 

$ py ~~-~~ 3.14 ~~-~~ m src.scripts.seed Seeding database... 

Generating users... 1@ users created Generating posts... 3@ posts created Generating follows... 36 follow relationships created Generating likes... 86 likes created Generating comments... 84 comments created Generating moments... 22 moments created 

Database seeded successfully. 

Sample credentials: 1. Email: scrosby@example.org, Password: password123, Role: moderator 2. Email: dgarcia@example.net, Password: password123, Role: user 3. Email: thomasashley@example.org, Password: password123, Role: user 

|$ py ~~-~~3|.14<br>~~-~~m uvicorn src.main:app ~~--~~reload ~~--~~port 3000<br>|
|---|---|
|INFO:|Will watch for changes in these directories:<br>['C:\\git\\CAB43~~2-~~serve~~r-~~sid~~e-~~python']|
|INFO:|Uvicorn running on http://127.0.0.1:3000 (Press CTRL+C to quit)|
|INFO:|Started reloader process<br>[28812] using WatchFiles|
|INFO:|Started server process<br>[34620]|
|INFO:|Waiting for application startup.|
|INFO:|Applicationstartupcomplete.|



## AWS 

You will be deploying into CAB432's shared AWS account, which has been pr ~~e-~~ scoped toa limited set of services ~~.~~ Your permissions are scoped to the services below ~~—~~ you cannot provision anything outside this list, so the right service for each requirement in the user stories is one of these ~~<u>:</u>~~ 

- « Identity & Access 

   - Amazon Cognito (user pools, groups) ~~:~~ configured to send authentication emails via the pre ~~-~~ 

      - provisioned, cours ~~e-~~ managed SES identity noreply@cab432.com 

   - IAM ~~:~~ a pr ~~e-~~ scoped role is provided ~~—~~ you cannot create new IAM users, roles, or policies 

- ¢ Networking & Edge 

eo Route53 ~~:~~ a shared, cours ~~e-~~ managed hosted zone 

   - API Gateway (HTTP API) 

   - eo AWS Certificate Manager (ACM) 

- « Compute 

o AWS Lambda ~~:~~ Python or Node. ~~j~~ s 

- ¢ Data 

   - eo DynamoDB: for metadata 

o §3 ~~:~~ for object (photos) storage 

- ¢ Observability & Governance 

o CloudWatch Logs ~~:~~ as developer tools to assist in this task ~~.~~ 

No other AWS services may be used. 

For each service, we have listed how you tell Gradescope you have implemented and integrated these services. 

You will tell Gradescope where to find your cloud resources by submitting a YAML file containing Amazon Resource Numbers (ARNs). 

###### Constraints 

- « All AWS resources must include the following tags ~~<u>:</u>~~ 

© qut ~~-~~ username : your Student email address (€ ~~.~~ g ~~.~~ nxxxxxxxx@qut.edu.au ) © purpose: “assessment 1" « All resources must be deployed in ap ~~-~~ southeast ~~-~~ 2 ~~.~~ « Lambda functions must use one of the following runtimes ~~:~~ o Node. ~~j~~ s 18 ~~.x~~ , 20 ~~.x~~ , or 22 ~~.~~ x o Python 3 ~~.~~ 11, 3 ~~.~~ 12, 3 ~~.~~ 13, or 3 ~~.~~ 14 

cloudInfrastructure.s3MediaStoreARN 

aws GH: (.Q Search [alt+s] @ a & @ (@! Ec2 ‘@® cloudwatch tam fl s3 Lambda PB aricateway [BB cognito [certificate Manager {| DynamoDB r=) Amazon S3 > Buckets > n10123456-s3-media iad Objects Metadata Properties Permissions Metrics Manage! Amazon $3 < —_—_—_—— v Buckets Bucket overview Goriarell purpose nulchate AWS Region Amazon Resource Name (ARN) Directory buckets Asia Pacific (Sydney) ap-southeast-2 (Bi arn:aws:s3:::n10123456-s3-media Table buckets Vector buckets 

- © Pick one language and use it consistently across your backend. 

- « Multi ~~-~~ factor auth is not required for this assignment ~~.~~ 

- ¢ Every resource name should include your studentID so ownership is traceable ~~.~~ Beyond that, naming conventions are up to you ~~.~~ 

- ¢ Cognito must be configured to send authentication emails (sig ~~n-~~ up verification codes, etc ~~.)~~ via the pre ~~-~~ provisioned SES identity noreply@cab432.com , Not Cognito's own default/built ~~-i~~ n email service. Cognito's default service enforces a low daily send quota shared across the whole course account ~~—~~ using the dedicated SES identity avoids exhausting it ~~.~~ 

###### Route 53 

Create a subdomain on cab432 ~~.~~ com so the API has a human ~~-r~~ eadable name ~~.~~ 

Tell us the subdomain you chose. 

YAML file key: 



<!-- Start of picture text -->
cloudInfrastructure.apiRouteS3Record<br><!-- End of picture text -->

You do not need to specify an ARN for Route53. Instead, in the YAML file, simply give us the ~~fully qualified domain name~~ ©: ~~(https://en.wikipedia.org/wiki/Fully_qualified_domain_name) (~~ € ~~.g~~ ., 10123456.cab432.com ) ~~.~~ Do not include protocols (e ~~.~~ g., http:// , https:// ) ~~.~~ Do not include trailing slash ( / ) ~~.~~ There should be three dot ~~-~~ separated segments to your domain: the subdomain, cab432 and com. 

Create a S3 bucket to store uploaded images. 

Structured data is not to be stored in S3 ~~.~~ 

YAML file key ~~:~~ 

The ARN of an S3 bucket is found in the S3 console ~~.~~ Be sure to switch to the 'Properties' tab of the bucket ~~:~~ 

###### Lambda 

cloudInfrastructure.cognitoARN 

Create Lambda functions that implement the core business of Strobe ~~.~~ We have provided source code for you but you need to make each controller Lambda- ~~c~~ ompatible ~~.~~ There should be one Lambda function per entity in the data model ~~.~~ 

You will specify a list of Lambda functions in the YAML under cloudinfrastructure.lambdaARN . 



<!-- Start of picture text -->
The ARN of a Lambda function is found in the Lambda console :<br>aws (GE (.Q Search Ats]@ ) BB @ | @ — Asiaractic sydnevd + anasz-reachingTeam/bradfos@aquteduau<br>Bi ec2 I clouawatch iam (ss BM tambda [A aricateway A) cognito [Ell certificate Manager {l DynamopB<br>= Lambda > Functions > n10123456-lambda-upload ® &<br>m10123456-lambda-upload<br>CED itil F unctione arcARN ‘lambda:ap-southeast-2:90144428095,<br>3:function:n10123456-lambda-upload<br>110123456-<br><!-- End of picture text -->

###### Cognito 

Create a user pool. 

Your submission must also include a pre ~~-~~ created test account ( testUsername / testPassword ) that already exists and is confirmed in your Cognito user pool ~~.~~ This account is used specifically for authenticatio ~~n-~~ focused checks (User Story 4) so grading doesn't depend on the timing of verifying a new user account ~~.~~ This account must also be a member of your designated privileged/admin Cognito group (User Story 5), since it doubles as the grader's privileged identity for authorization checks ~~.~~ 

YAML file key: 

The ARN of a Cognito User Pool is found in the Cognito console ~~:~~ 



<!-- Start of picture text -->
fe EC2 (€@ CloudWatch 1AM =—§S3 [BX Lambda ‘API Gateway E@ Cognito [x]<br><!-- End of picture text -->

e Amazon Cognito > User pools > n10123456-cognitoauth > Overview 



<!-- Start of picture text -->
Amazon Cognito < Overview: n10123456-cog<br>Current user pool View all<br>User pool information<br>n10123456-cognitoauth v User pool name<br>n10123456-cognitoauth<br><!-- End of picture text -->



<!-- Start of picture text -->
Overview User pool ID<br>IE) ap-southeast-2_xyYAifjUD<br><!-- End of picture text -->

v Applications App clients ARN RSnSe es Vie t-2:901444280953:userpool/ap-southI) arn:aws:cognito-idp:ap-southeas v User management east-2_xyYAifjUDyn 

###### DynamoDB 

Create a database for each entity in the data model. You will specify a list of DynamoDB tables in the YAML under cloudInfrastructure.dynamoDBTableARNs ~~.~~ The ARN of a DynamoDB table is found in the DynamoDB console ~~:~~ 



<!-- Start of picture text -->
as @ HQ faites} ©<br>BB ec2 Bctoudwatch Bum ss Gramoda PP aricateway BB cognito [certificate Manager [ Dynamove<br>[=] DynamoDB > Tables > yu39-poc-a1-grader-ddb-users<br>DyramoDB, “WF ratte (0) <  10123456-ddb-users<br>Dashboard<br>Tables posed v Settings Indexes Monitor Global tables Backups Exports and s<br>Explore items: Filter by tag value<br>_ editor General information in‘o<br>Exports to $3 Q Find tables Partition key Sort key<br>user_id (String) .<br>Imports from $3<br>Integrations 1. 8 Alarms Point-in-time recovery (PITR) Info<br>@ No active alarms @on<br>Settings Average item size Resource-based policy info<br>278.86 bytes © Not active<br>Clusters<br><!-- End of picture text -->

###### API Gateway 

Create and stage the API. You must use a HTTP API. In this assignment, we want you to use HTTP and not REST API ~~.~~ 

- ¢ YAML file key: 



<!-- Start of picture text -->
cloudInfrastructure.apiGatewayExecutionARN<br><!-- End of picture text -->

- « YAML file key: cloudInfrastructure.apiGatewayStageARN 

- The ARN for API Gateway resources are ones you must curate yourself ~~.~~ The ARNs do not appear <u>in</u> the web console. 

Our sample YAML file looks like this ~~:~~ 

cloudInfrastructure: apiGatewayExecutionARN: arn:aws:e ~~x~~ ecu ~~t~~ e-api ~~:~~ ap-southeast-2:901444280953 : wowvqi544k apiGatewayStageARN: arn:aws:apigateway:ap ~~-~~ southeast ~~-2~~ ::/apis/w9wvqi544k/stages/$default 

There are two segments you need to manually update ~~:~~ 

1. You need to replace wowvqisaak with the identifier of your API Gateway, which can be found in the API Gateway console: 



<!-- Start of picture text -->
aws G@ = | Q am @ Ask AmazonQ X B® | B Asia pacitid<br>() ec2  @l cloudwatch tam ss Lambda A apiGateway ‘Bg cognito [& certificate Manager<br>r=) API Gateway > APIs<br>API Gateway <<br>APIs<br>APIs<br>Custom domain names | Q Find APIs<br>Domain name access associations<br>VPC links Name a Description v ID v |<br>AgentCore targets " .<br>n10123456-api wowvqi544k<br><<br><!-- End of picture text -->

2 ~~.~~ You need to replace default with the name of your stage, which can be found in the API Gateway ‘stages' console ~~:~~ 

aws 8 Ht Q acm 

GAskAmazonQ X 

“Le @ 83 4 

Rl ec2 (WH ctoudwatch iam Sls3) tambda ff aricateway (BB cognito [certificate Manager 

e API Gateway > APIs > n10123456-api (w9wvqi544k) > Stages 

API Gateway < 

#### Stages 



<!-- Start of picture text -->
APIs<br><!-- End of picture text -->



<!-- Start of picture text -->
Custom domain names<br>Domain name access associations<br><!-- End of picture text -->



<!-- Start of picture text -->
Stages for n10123456-<br>api<br><!-- End of picture text -->



<!-- Start of picture text -->
Stage details<br><!-- End of picture text -->



<!-- Start of picture text -->
Name<br>Q Search $default<br><!-- End of picture text -->

API: yu39-poc-a1-gra... (w9wvqi544k) 



<!-- Start of picture text -->
© $default<br><!-- End of picture text -->



<!-- Start of picture text -->
Invoke URL<br>;<br>https://w9wvqi544k.exed<br><!-- End of picture text -->

###### Certificate Manager 

Create a certificate for your subdomain of cab432 ~~.~~ com 

YAML file key: cloudiInfrastructure.certificateARN 

The ARN of a certificate is found in the Certificate Manager console ~~:~~ 



<!-- Start of picture text -->
ows GOH: [.Q Search [alt+s]@<br>i ec2 @Betoudwatch By iam fHs3 GM tambda (PP aricateway BB cognito [RF certificate Manager<br><!-- End of picture text -->



<!-- Start of picture text -->
(=) AWS Certificate Manager > Certificates > 44158f75-1d82-4e48-b149-99276bb57d2a<br>AWS Certificate < 44158f75-1d82-4e48-b149-99276bb57d2a<br>Manager (ACM)<br>List certificates Certificate status<br>Request certificate Identifier<br>Import certificate 44158f75-1d82-4e48-b149-99276bb57d2a<br>AWS Private CA uN<br>[ arn:aws:acm:ap-southeast-2:901444280953:certificate/44158f75-1d82-4e48-b149-99276bb57d2a<br>v ACME Type<br>ACME certificates New Amazon Issued<br>Endpoints New<br><!-- End of picture text -->

### What you need to do 

For 30 marks, you need to ~~:~~ 

- ¢ Implement a serverless stack 

- « Adapt a standalone server app to function in that serverless stack 

- « Have the API pass the User Acceptance Testing 

- « Address the ten user stories, below ~~.~~ 

In this assignment, you will build the cloud infrastructure for Strobe ~~.~~ Your goal is to design and implement the infrastructure using serverless, event ~~-d~~ riven technologies, including ~~:~~ S3, Lambda, DynamoDB, API Gateway, Route 53, Cognito and ACM ~~.~~ 

You must integrate the cloud services, building a software system that is low ~~-~~ cost and scalable ~~.~~ The intention is not to simply create cloud resources ~~--~~ it is about the integration of these and therefore, correct configuration. 

Continue reading to know what you need to achieve with each service. Remember, CAB432 is not really about software development ~~:~~ it is about computing in the cloud ~~.~~ 

Your submission will be autograded by Gradescope and you are allowed unlimited attempts ~~.~~ You will submit two YAML files that point Gradescope at your implementation ~~.~~ Gradescope will verify that the cloud resources exist, are correctly configured and your platform passes the user acceptance testing ~~.~~ 

Most of the application code has been provided ~~.~~ Your job is to make adjustments to the code, as necessary, and deploy the app into a serverless cloud. 

Each user story is worth 3 marks, split evenly across its acceptance criteria, for a total of 30 marks ~~.~~ 

###### User Story 1: Secure Public Access (3 marks) 

As a user, | want to securely access the platform's API via HTTPS so that my data is protected in transit ~~.~~ Acceptance Criteria ~~:~~ 

- ¢ Avalid, trusted certificate is issued and covers the domain used to reach the API (1) 

- ¢ The API is exposed through a custom, human ~~-r~~ eadable domain rather than a raw cloud ~~-p~~ rovider ~~-~~ 

   - generated endpoint (1) 

- « The endpoint enforces a modern, secure minimum TLS version (1) 

###### User Story 2: Meaningful Domain Access (3 marks) 

As a user, | want to reach the API using a memorable domain name so | don't need to remember a cloud ~~-~~ provide ~~r-~~ generated URL. 

Acceptance Criteria: 

- « ADNS record is configured for the chosen domain (1) 

- « The domain resolves correctly via public DNS (1) 

- « Requests to the domain are correctly routed to the deployed API (1) 

###### User Story 3: User Registration (3 marks) 

As a new user, | want to register an account so | can use the platform ~~.~~ Acceptance Criteria: 

« Registration creates a real, durable identity in a managed identity service, and a corresponding app ~~-l~~ evel row in DynamoDB ~~—~~ not one or the other (1.25) 

- « Each registered user has a unique, immutable identifier (1) 

- ¢ Duplicate account creation (e ~~.~~ g ~~.~~ re ~~-~~ registering the same identity) is rejected (0 ~~.~~ 5) 

- ¢ Cognito is configured to send authentication emails via the required shared SES identity, not its own default email service (0.25) 

###### User Story 4: Authentication (3 marks) 

As a registered user, | want to log in securely so | can access my account ~~.~~ 

Acceptance Criteria ~~:~~ 

- ¢ Valid credentials return a usable session/access token (0.75) 

- ¢ Invalid credentials are rejected with an appropriate, non ~~-l~~ eaky error response (0 ~~.~~ 75) ¢ Sessions/tokens are not valid indefinitely ~~—~~ they expire within a reasonable window (no longer than 24 hours) (0.75) 

- « The pre ~~-~~ created test account supplied in your submission can also successfully log in (0 ~~.~~ 75) 

###### User Story 5: Authorization & Account Management (3 marks) 

As a system owner, | want privileged actions restricted to trusted users, and users should be able to remove their own account ~~.~~ 

Acceptance Criteria: 

- « Privileged operations are gated by group/role membership in the identity service ~~—~~ the graded privileged action is content moderation, specifically hiding another user's post via post /v1/posts/:id/hide (moderator ~~-o~~ nly) (1 ~~.~~ 5) 

- « Aregular (non ~~-p~~ rivileged) user attempting a privileged action is rejected (0 ~~.~~ 5) 

- « Auser can delete their own account through the API, and this actually deprovisions their identity in Cognito (not just app ~~-l~~ evel data) (1) 

###### User Story 6: Create Content (3 marks) 

As a user, | want to create a post so | can share content ~~.~~ Acceptance Criteria ~~:~~ 

- « An authenticated request creates a new post via the API (1) 

- « Post metadata (author, caption, timestamp, image reference) is durably persisted ~~—~~ and so are comments and likes created on a post, each independently verified against DynamoDB (1.25) 

- « Each post has a unique identifier and is retrievable by it afterward (0 ~~.~~ 75) 

###### User Story 7: Secure Image Upload (3 marks) 

As a user, | want to upload images securely so | can attach photos to posts ~~.~~ 

Acceptance Criteria ~~<u>:</u>~~ 

- « The backend issues a short ~~-l~~ ived, scoped upload credential for a specific object (short ~~-l~~ ived meaning it expires within 5 minutes) (1) 

- ¢ The client can upload directly to storage using only that credential ~~—~~ no long ~~-l~~ ived AWS credentials are ever exposed to the client (1) 

- ¢ The uploaded object lands in the correct location, unambiguously associated with the requesting user/post (1) 

###### User Story 8: Content Retrieval (3 marks) 

As a user, | want to retrieve posts and their images through the API so the provided frontend can display them. 

Acceptance Criteria ~~<u>:</u>~~ 

- ¢ The API returns content in a wel ~~l-~~ formed, consistent shape suitable for a client to render (1) 

- ¢ Retrieval reflects real persisted data, not a static or hardcoded response (1) 

- « Associated media is retrievable only via a short ~~-l~~ ived access mechanism, never a permanent public link (1) 

###### User Story 9: Secure Data Storage Design (3 marks) 

As a system owner, | want data stored securely so only legitimate operations can read or write it ~~.~~ 

Acceptance Criteria ~~<u>:</u>~~ 

- ¢ Object storage blocks all public access at the bucket level (0.75) 

- « Media objects are inaccessible by any means other than the short ~~-l~~ ived access mechanism from User Story 7/8 (1) 

- ¢ All write operations against the API require authentication (1) 

- ¢ Data is recoverable from accidental loss or corruption ~~<u>:</u>~~ DynamoDB point ~~-~~ i ~~n-~~ time recovery is enabled with a 7 ~~-~~ day retention window (not the 35 ~~-~~ day default) (0 ~~.~~ 25) 

###### User Story 10 ~~:~~ End ~~-to-~~ End Integration (3 marks) 

As an instructor, | want the whole system to function end ~~-t~~ o ~~-~~ end against the provided frontend, using an approved, scalable architecture ~~.~~ 

Acceptance Criteria ~~<u>:</u>~~ 

¢ If Gradescope cannot detect the cloud resource having qut ~~-~~ username correctly set to match <studentDetail:studentID>@qut.edu.au ¢ If your cloud resource does not exist in ap ~~-~~ southeast ~~-~~ 2 ¢ If you add or remove keys from the YAML file Below is an example ~~.~~ Use this as a starting point ~~.~~ A few notes about it ~~<u>:</u>~~ « The CAB432 AWS account number is 901444280953 . If you do not use that account, you will fail the tests ~~.~~ 

- « The provided frontend, pointed at your deployed backend, can complete the full flow ~~<u>:</u>~~ register > log in > create a post — upload an image — follow another user, and the follow itself is verified to actually persist in DynamoDB (0.5) 

- « Deployed resources carry the required qut ~~-~~ username / purpose tags for traceability (0 ~~.~~ 75) « All compute functions run on an approved runtime only (0.5) 

- « Routes are distributed to a sensible separation of concerns rather than a single monolithic compute handling every route (1 ~~.~~ 25) 

   - © This is verified against submission ~~-~~ routes.yml (see Submission Requirements) ~~:~~ every declared route genuinely integrates with its declared Lambda, every declared storage resource exists 

   - eo A"moment" created via the API is confirmed to persist in its declared DynamoDB table (the other entities ~~—~~ user, comment, like, follow ~~—~~ have their own persistence checks under User Stories 3,6 and 10 respectively. 

   - The declared DynamoDB tables and Lambda functions must also be genuinely distinct per entity/controller, not one shared table or a single monolith Lambda behind every route. 

### Submit YAML to Gradescope 

When submitting your assignment, you must provide two YAML files ~~<u>:</u>~~ submission ~~-~~ infra.yml and <u>submission</u> ~~<u>-</u>~~ <u>routes.yml</u> . The files must follow the structures below exactly, with all required fields filled in ~~.~~ The values shown are examples; you must replace them with your actual deployment values. Your submission must also include a pre ~~-~~ created test account( testUsername / testPassword ) that already exists and is confirmed in your Cognito user pool ~~.~~ This was described in more detail earlier, in the Cognito section of this page. 

|Toreceivemarks~~:~~|
|---|



- « You must tell Gradescope which cloud resources are yours by specifying the Amazon Resource Number (ARN) 

- « You must provide your student details in the file 

You will not receive any marks for a test: 

|Ifthecloudresourcedoesnotexist|
|---|



- ¢ If Gradescope cannot detect the cloud resource having 

Below is an example ~~.~~ Use this as a starting point ~~.~~ A few notes about it ~~<u>:</u>~~ 

###### Sample YAML 

© cloudInfrastructure.lambdaARN is required 

###### submission- ~~i~~ nfra ~~.~~ yml 

- cloudInfrastructure: apiGatewayExecutionARN: arn:aws:execute ~~-a~~ pi :a ~~p-~~ southeast ~~-~~ 2:901444280953 : abc123 apiGatewayStageARN: arn:aws:apigateway:ap ~~-~~ southeast ~~-~~ 2::/apis/w9wvqi544k/stages/$default apiRoute53Record: n1@123456.cab432.com certificateARN: arn:aws:acm:ap ~~-~~ southeast ~~-~~ 2:901444280953:certificate/abc123 cognitoARN: arn:aws:cog ~~ni~~ to- ~~id~~ p:ap-s ~~ou~~ theast-2:901444280953:userpool/abc123 dynamoDBPostsTableARN: arn:aws: ~~d~~ yna ~~m-~~ 2:901444280953odb:ap-south : table/n10123456 ~~e-~~ ddba ~~s-~~ postt s3MediaStoreARN: arn:aws:s3:::n10123456 ~~-~~ strobe ~~-~~ media dynamoDBTableARNs: 

- entity: user arn: arn:aws:dynamodb: ap ~~-~~ southeast ~~-~~ 2:901444280953: table/n10123456 ~~-~~ ddb ~~-u~~ sers 

- ~~-~~ entity: post arn: arn:aws:dynamodb:<sup>a</sup><sup>~~p~~-sou</sup><sup>~~t~~heast-2:9014442</sup> : table/n10123456<sup>~~8~~</sup> ~~-~~ ddb<sup>0</sup><sup>~~9~~</sup> ~~-p~~<sup>53</sup> ost 

- ~~-~~ entity: comment arn: arn:aws:dynamodb: ap ~~-~~ southeast ~~-~~ 2: 901444280953: table/n10123456 901444280953: table/n10123456 table/n10123456 ~~-~~ ddb ~~-~~ comments 

- ~~-~~ entity: like arn: arn:aws:dyna ~~m~~ odb:a ~~p~~ -southeast-2:90144: table/n10123456 ~~42-~~ ddb8 ~~0-~~ likes953 

- ~~-~~ entity: follow arn: arn:aws:dynamodb: ap ~~-~~ southeast ~~-~~ 2:901444280953: table/n10123456 ~~-~~ ddb ~~-~~ follows 

- ~~-~~ entity: moment arn: arn:aws:dyn ~~am~~ odb: ~~ap~~ -southeast-2:90144: table/n10123456 ~~-4~~ ddb2 ~~8-~~ moments0953 

- lambdaaRN: 

- entity: comment arn: arn:aws:dynamodb: ap ~~-~~ southeast ~~-~~ 2: 901444280953: table/n10123456 901444280953: table/n10123456 table/n10123456 ~~-~~ ddb ~~-~~ comments 

- controller: auth 

- arn: arn:aws: lambda: a ~~p~~ -so ~~ut~~ heast-2:9014442function :n10123456 ~~8-~~ lambda09 ~~53-a~~ uth: 

- ~~-~~ controller: feed arn: arn:aws: lambda: a ~~p~~ -so ~~ut~~ heast-2:9014442function :n10123456 ~~8-~~ lambda09 ~~53-f~~ eed: 

- ~~-~~ controller: moment arn: arn:aws: lambda: ap ~~-~~ southeast ~~-~~ 2:901444280953: function :n1@123456 ~~-~~ 1ambda ~~-m~~ oment 

- ~~-~~ controller: post arn: arn:aws: lambda: a ~~p~~ -so ~~ut~~ heast-2:9014442function :n10123456 ~~8-~~ lambda09 ~~53-~~ post: 

- ~~-~~ controller: user arn: arn:aws: lambda: a ~~p~~ -so ~~ut~~ heast-2:9014442function :n10123456 ~~8-~~ lambda09 ~~53-u~~ ser: 

- ~~-~~ controller: upload arn: arn:aws: lambda: ~~ap~~ -so ~~u~~ theast-2:901444 ~~2~~ 80 ~~95~~ 3: 

- metaData: function :n10123456-lambda-upload 

|qutUsernameTag:<br>n10123456@qut.edu.au|
|---|
|testUsername:<br>user@test.com|
|testPassword:<br>SomeStr@ngPassword!|
|studentDetail:|
|studentID:<br>FILL|
|studentFirstName:<br>FILL|
|studentLastName:<br>FILL|



- © cloudInfrastructure.metaData.qutUsernameTag 

   - © Itis your qut ~~-~~ username tag value, verified against the tags actually applied to your deployed resources, and it's what the grader uses to generate unique, collision ~~-~~ free test data for your run. 

e 

- cloudInfrastructure.dynamoDBTableARNs 

- Every DynamoDB table you've deployed must be entit ~~y-~~ tagged 

(user / post / comment / like / follow / moment ). 

- The grader confirms every ARN you list actually resolves to a real table, and that the entry tagged post matches your dynamoDBPostsTableARN 

- These declarations are the source for verifying persistence across User Stories 3, 6 and 10 

- © ~~i.~~ e ~~.,~~ the grader confirms that creating a user/comment/like/follow/moment hasa record created in the relevant table, as you declare ~~.~~ 

- The tables must also be genuinely distinct per entity ~~—~~ declaring the same physical table under multiple entity tags will fail that check ~~.~~ 

© This section follows the same schema as cloudinfrastructure.dynamoDBTablearNs but for Lambda functions ~~.~~ 

###### submission ~~-r~~ outes.yml 

This file maps every API route to the infrastructure that is involved generating the response ~~.~~ Do not add or remove routes from this file ~~.~~ We have provided all the routes you need. 

The schema for a route is: 

~~-~~ route: <URL from standalone app> method: <HTTP method> controller: <controller name> apiGatewayRoute: ANY <URL from API Gateway> # "ANY" is a HTTP request method lambdaARN: <arn> storage: {entity: <name>, arn: <arn>} # Usually the primary DynamoDB table additionalstorage: [ {entity: <name>, arn: <arn>} ] # Any additional storage, like S3 or DynamoDB tables 

In the template file, we have prefilled the route , method , and controller fields ~~.~~ These are fixed for all submissions because the interface to your server must match our implementation otherwise client apps (Strobe Web and the Insomnia collection) will break ~~.~~ 

You must complete ~~:~~ 

- © apiGatewayRoute You specify this value. It is the AP] Gateway route key that receives requests for the application route and forwards them to the appropriate backend integration ~~.~~ This is the route configured in your API Gateway, not the standalone app route ~~.~~ 

- ¢ lambdaarn : Gradescope will check that the specified Lambda function is invoked by the API Gateway route. 

¢ storage (the primary DynamoDB table or S3 bucket accessed by the route, if any) 

If this file is omitted, the autograder cannot perform the routing manifest checks and will result in loss of marks. 

Gradescope will verify route integrations, storage resources, per ~~-e~~ ntity data, and that each controller is served by a distinct Lambda function. 

##### YAML in depth 

If you have not used YAML before, read this section first. YAML is the format used for the files you submit ~~.~~ YAML™ (rhymes with “camel”) is a human- ~~fr~~ iendly, cross language, Unicode based data serialization language designed around the common native data structures of agile programming languages ~~.~~ It is broadly useful for programming needs ranging from configuration files to Internet messaging to object persistence to data auditing. 

YAML (a recursive acronym for “YAML Ain’t Markup Language”) is a data serialization language designed to be human- ~~fr~~ iendly and work well with modern programming languages for common everyday tasks ~~.~~ Source: https://yaml ~~.~~ org/spec/ 

Some useful YAML references: 

« ~~YAML quick reference~~ &; ~~_(https://quickref.me/yaml.html)~~ 

« ~~YAML cheat sheet~~ E; ~~(https://gist.github.com/xputerax/70a32929bf2603ed65990cc3550902a8)~~ 

We will use submission ~~-~~ infra.yml as an example ~~:~~ 

cloudInfrastructure: apiGatewayExecutionARN: <arn> apiGatewayStageARN: <arn> apiRoute53Record: <domain ~~-~~ name> certificateARN: <arn> cognitoARN: <arn> dynamoDBPostsTableARN: <arn> dynamoDBTableARNs: [ {entity: <name>, arn: <arn> } ] lambdaARN: [list of ARNs] 

The YAML document contains a single top ~~-l~~ evel key named cloudinfrastructure <u>.</u> This key contains all information required to describe the application's deployed AWS resources ~~.~~ The structure acts as a deployment manifest, allowing automated tools to identify the cloud resources used by the application ~~.~~ 

Each value in YAML is associated with a key ~~.~~ Keys are organised hierarchically through indentation ~~.~~ For example ~~:~~ 

cloudInfrastructure: apiGatewayExecutionARN: <arn> 

The key apicatewayExecutionarn is a child of cloudinfrastructure . When referring to keys using dot notation, such as: 

cloudinfrastructure.apiGatewayExecutionARN 

this means to first locate the top ~~-l~~ evel key cloudInfrastructure , then access its child key apiGatewayExecutionARN <mark>.</mark> Akey followed by [] indicates that the value is an array (also called a list) ~~.~~ For example ~~<u>:</u>~~ 

cloudInfrastructure.dynamoDBTableARNs|[} 

means that dynamopBTablearNs contains multiple values rather than a single value. Arrays are represented in YAML using a dash ( ~~-~~ ) before each item. For example: cloudInfrastructure: dynamoDBTableARNs: ~~-~~ {entity: <name>, arn: <arn>} ~~-~~ {entity: <name>, arn: <arn>} ~~-~~ {entity: <name>, arn: <arn>} The dynamopgtablearNs key contains an array of objects ~~.~~ Each object contains two child keys ~~:~~ 

* entity : the name of the application entity represented by the table ¢ arn: the ARN of the DynamoDB table Similarly, 1ambdaarn contains an array of objects, and uses the same schema as dynamoDBTableARNs ~~.~~ 

Not every resource is represented as an array ~~.~~ For example, s3Mediastorearn contains a single ARN because the application is expected to use only one S3 bucket for media storage: 

cloudInfrastructure: s3MediaStoreARN: <arn> 

The key dynamoDBPostsTablearn is a required special case ~~.~~ This key must always be included because the application relies on this DynamoDB table for core functionality ~~.~~ 

The YAML file contains additional keys beyond those shown above ~~.~~ These follow the same structure: each key identifies a particular cloud resource or piece of deployment metadata. 

The following keys identify shared AWS resources used by the application: 

- © apiGatewayExecutionarn identifies the deployed API Gateway API ~~.~~ 

- © apiGatewayStagearn identifies the API Gateway stage ~~.~~ 

- © apiRoute53Record identifies the public DNS record used to access the application ~~.~~ 

- certificatearn identifies the TLS certificate used for HTTPS ~~.~~ 

- © cognitoarn identifies the Amazon Cognito user authentication resource ~~.~~ 

The metadata key stores additional deployment and testing information ~~.~~ They are required by Gradescope. 

###### Example: 

cloudInfrastructure: metadata: qutUsernameTag: <qut ~~-~~ username ~~-~~ at ~~-~~ qut ~~-~~ edu ~~-a~~ u> testUsername: <username> testPassword: <password> 

###### The metadata fields are ~~:~~ 

- qutUsernametag ~~<u>:</u>~~ identifies the student's deployed resources ~~.~~ 

- * testUsername ~~<u>:</u>~~ credentials for a test user account ~~.~~ * testPassword <mark>:</mark> password for the test user account. 

Keeping infrastructure details and metadata in the same YAML document allows the deployment and grading systems to automatically locate resources, execute tests, and verify the submitted application ~~.~~ 

###### Submission 

You will submit two YAML files to Gradescope ~~.~~ We have provided templates ~~.~~ You need to fill out the fields with the appropriate Amazon Resource Numbers (ARNs), etc ~~.~~ This was described earlier ~~.~~ 

Gradescope will interogate the CAB432 AWS account, checking for the existence and correct configuration of the cloud resources you specify in the YAML file ~~.~~ It will also check the behaviour of the app by acting as an agent (user) of Strobe. 

Your cloud resources must be appropriately tagged with qut ~~-~~ username and exist beyond the due date ~~.~~ 

For the purposes of assessment, after the due date, we may trigger a r ~~e-~~ grading of the most recent submission. 

If we detect you have specified the cloud resource of another student, an academic misconduct case will be substantiated. 

###### Feedback 

This assignment is automatically marked by Gradescope. The autograder was designed, implemented and tested by CAB432 staff ~~.~~ It will provide to you feedback about your submission ~~.~~ 

After the due date, we may provide general feedback to the class however, we will not provide individual feedback unless necessary or requested ~~.~~ 

###### Moderation 

The autograder may be updated during the period you are working on the assignment ~~.~~ That could be because of bug fixes or new features ~~.~~ Gradescope will tell you which version of our autograder assessed your submission ~~.~~ If Gradescope has been upgraded since you last submitted, a changelog will appear after grading of your latest submission has finished ~~.~~ 

The source code of the Gradescope autograder has been written by artificial intelligence and humans ~~.~~ All source code has been thoroughly reviewed and tested by CAB432 staff. For the purposes of academic integrity, we cannot make the source code of the autograder available to you, however you are free to discuss with us any concerns or general queries you have about the grading system ~~.~~ 

### Change log 

¢ 24 July 2026 

Updated API Gateway specification to indicate HTTP API must be used and not REST API ~~.~~ 

° 22 July 2026 

Initial deployment for CAB432 ~~_2~~ 6se2 

TEQSA PRV12079 | CRICOS 00213J | ABN 83 791 724 622 

