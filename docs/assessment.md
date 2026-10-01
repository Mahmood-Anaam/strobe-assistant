Overview

You will use cloud services and cloud architectures to integrate artificial intelligence platforms into an application. You will demonstrate your deployment to teaching staff during the practicals, including an oral Q\&A.

This is a [Verified Identity Assessment](https://qutvirtual4.qut.edu.au/group/student/study/classes-and-readings/verified-identity-assessments).

**This assignment has two tracks that you can choose from. You only need to complete one.**

Strobe survived Assessment 1\. The API is serverless, scalable, and no longer falls over during a traffic spike....

* Track A: ...but Strobe's product team has a new problem: users have thousands of photos and no way to make sense of them. They want something that can answer "find me the photos of my dog," or turn an album into a narrated slideshow.

* Track B: ...meanwhile, Strobe's own engineering team is drowning in a backlog of GitHub issues nobody has time to triage.

Both tracks have the same shape: an AI agent that can retrieve relevant context, call tools against real data, and run both on-demand and on a schedule. This assignment asks you to build the AI agent and the cloud infrastructure it needs.

You will choose one of two tracks:

* Track A: Strobe Assistant. Build an agent that talks to *your own* Assessment 1 Strobe backend. It could, for example, provide semantic search over a user's posts and photos, narrate summaries, or automatically classify newly uploaded images.

* Track B: Repository Custodian. Build an agent that manages a small Git repository on your behalf. It could, for example, triage new issues, summarise bug reports, or keep documentation tidy.

Track A continues the Strobe story and reuses infrastructure you already have. Track B is the option if your Assessment 1 isn't in a state you want to build on. It's a fresh, self-contained problem with its own (smaller) surface area. Neither track is assessed as "harder" than the other. Both exercise the same underlying cloud-native agent architecture.

Regardless of track, the graded shape of the system is the same: a foundation model accessed through Amazon Bedrock, a vector store for retrieval, an MCP server exposing tools to the model, at least one event-driven (asynchronous) workflow, and at least one autonomous scheduled ("heartbeat") run — all wired together as managed, serverless AWS infrastructure rather than a single long-running process.

**This assessment item is eligible for the 48 hour extension. You can read more information about this on the [HiQ website](https://qutvirtual4.qut.edu.au/group/student/study/assignments/submitting/late-assignments-and-extensions).**

Unit Learning Outcomes assessed

* ULO1 Discuss the elastic nature of cloud technologies and business models and their application in technical, commercial and sustainability contexts.

* ULO2 Analyse application design and implementation requirements to select suitable cloud infrastructure and software services from a range of XaaS offerings.

* ULO4 Design and implement scalable cloud applications using industry standard languages and APIs, deployed on a public cloud infrastructure and leveraging a range of cloud services.

| Weighting | Group or Individual | How I will be assessed |
| :---- | :---- | :---- |
| 30% of final grade | Individual | Grade out of 30 |

Attachments

* Template of infrastructure YAML: [submission-agent-infra.yml](https://canvas.qut.edu.au/courses/23778/files/9294551/download)

* ACP WebUI chat client: [CAB432-ACP-WebUI-1.0.0.zip](https://canvas.qut.edu.au/courses/23778/files/9247210/download)

The ACP WebUI archive contains the client's source code: a browser chat client that speaks the Agent Client Protocol, plus a deterministic ACP test agent you can run locally (see its README) so you can build and check the front end before your backend exists. See core requirement 4, below.

Understanding the assignment

Track A: Strobe Assistant

Your agent sits in front of your own Assessment 1 backend and gives users a conversational way to explore their content:

* Answer natural-language questions over a user's own posts/photos (e.g. "find me the photos of my dogs") using retrieval over embedded post/comment/caption data, not a keyword search.

* Turn a set of photos into a narrated album: a short generated story describing what's in them, in the user's own words as far as the LLM can manage.

* Automatically classify newly uploaded images (what's in the photo) as an asynchronous side-effect of upload, and persist the classification back into your data model. This cannot be done synchronously in the upload request handler.

* Optionally generate scheduled retrospectives ("on this day…", monthly recaps) without a user asking for them.

The data model must be expanded beyond the six entities from Assessment 1, this assignment introduces (naming indicative, not prescriptive):

* Embedding/Chunk: the unit stored in your vector store: an image's embedding vector, and a reference back to the image (eg. unique image ID).

* Classification result: attached to a Post/image: labels or tags produced by the async classification workflow, plus a timestamp.

* Agent run / memory record: a log of each scheduled/heartbeat invocation: what it did, when, and any summary it produced. This is what lets the agent build on previous runs rather than starting cold every time.

Track B: Repository Custodian

Your agent manages a Git repository rather than a photo library:

* On a recurring schedule (a "heartbeat"), check the repository for new issues and summarise/triage them.

* Investigate and comment on flagged issues, and keep documentation up to date where it has clearly drifted from the code.

* Retrieve relevant context about the repo (README, existing docs, past issues) via the vector store rather than re-reading the entire codebase on every run.

* You are not being asked to build a general coding agent that edits arbitrary large codebases: pick or fork a small project so the scope stays bounded.

The data model for this track is entirely up to you, though we are expecting one of similar size and complexity to Track A.

Core requirements (both tracks)

Every submission, regardless of track, must include:

1. A foundation model integration via Amazon Bedrock. Do not use another LLM provider.

2. **Amazon S3 Vectors** used for nearest-neighbour search over embeddings.

3. An MCP server: a dedicated middleware service exposing your data (Strobe API, or the Git repo/issue tracker) to the model as tools, deployed as its own component rather than folded into the model-calling code.

4. A conversational front end: the provided ACP WebUI (or a similar ACP-compatible chat client) pointed at your backend, so a marker can hold an actual conversation with your agent. The client is linked under *Attachments*, above. For both tracks, the marker must be able to send and receive images inline in the chat (the provided client supports both directions).

5. At least one event-driven, asynchronous workflow: e.g. an S3 upload triggering a queued classification job whose result is later persisted, rather than everything happening inline in a request/response, or repo issues/pull-request queued for processing by the agent.

6. At least one autonomous, scheduled run: an EventBridge-scheduled invocation of your agent that does something without a human prompting it in the moment.

7. Secrets/Parameters Manager: for any credentials/API keys your services need; nothing hard-coded, nothing in plaintext environment variables in your source.

8. At least one suitable component deployed on **Amazon ECS**.

AWS

You remain scoped to the CAB432 shared account, in ap-southeast-2. The purpose tag must be set to assessment 2\. If you are reusing cloud resources from the previous assignment, retag them as assessment 2\. Use 'AWS Resource Explorer' in the web console to find all of your existing cloud resources.

New services for A2

This assignment extends the Assessment 1 service list with the following:

* Amazon S3 Vectors

  * Managed vector database: vector buckets/indexes with nearest-neighbour search.

* AI/ML

  * Amazon Bedrock

  * The available models are listed below and on the AWS services available page.

  * We are using small, low-cost models, because the goal is assessing your *infrastructure*, not the quality of the model's output.

* Compute

  * Amazon ECS (Fargate): **required** (core requirement 8). Use it for your MCP server, agent, and/or conversational front end; the provided ACP WebUI includes a Dockerfile, so it can be containerised and deployed to ECS as your front end. (The vector store is Amazon S3 Vectors, so it does not need a container.)

  * AWS Lambda (Node.js/Python, same runtime constraints as Assessment 1\)

* Messaging & Events

  * Amazon SQS: decouples your async workflow (e.g. classification) from the request that triggers it.

  * Amazon EventBridge: both for the S3-upload-triggers-a-job path, and for scheduled ("heartbeat") invocations.

* Security

  * AWS Secrets Manager: required for any credential your services depend on.

* Data

  * DynamoDB: new tables/fields as above.

  * S3: storage of unstructured data (e.g. photos, repo snapshots).

  * (Amazon S3 Vectors is listed above; it is a separate service from S3.)

* Identity

  * Cognito: user identity management

* Observability

  * CloudWatch Logs, as before.

Constraints

* All resources tagged qut-username and purpose: "assessment 2".

  * Be sure to retag any purpose: assessment 1 resources otherwise they might be deleted.

* All resources in ap-southeast-2, in the CAB432 shared account.

* Same Lambda runtime constraints as Assessment 1, where Lambda is used.

* Resource names should include your studentID.

What you need to do

There is no functional autograder for this assignment. Unlike Assessment 1, Gradescope will only verify that the resources you declare exist, are correctly tagged, and are in-region. It will not exercise your API end-to-end. Marks for functionality and design come from an oral presentation, where you walk a marker through what you built.

To prepare for that presentation, and to help Gradescope generate a marking aid for your tutor, each declared resource in your submission YAML must include a short plain-language description of what it does (see Submission, below).

At minimum, be ready to demonstrate, live:

* A real conversation with your agent through the chat front end, including at least one retrieval-grounded answer (i.e. the model is visibly using your vector store, not just its own training knowledge).

* The asynchronous workflow actually firing, e.g. upload an image and show the classification landing a few seconds later, or point to logs showing the queue being consumed.

* Evidence of at least one scheduled/autonomous run having happened without you triggering it manually (e.g. a memory record, a generated digest, a triage comment with a timestamp that predates the demo).

* Your MCP server as a genuinely separate component from your chat front end and from the model call itself. You should be able to explain what tools it exposes and why they're structured that way.

Your goal is to design and implement the infrastructure using serverless, event-driven technologies, including: S3, Lambda, DynamoDB, API Gateway, Route 53, Cognito, ACM, Bedrock, EventBridge, ECS, SQS, Secrets Manager and Parameter Store.

You must integrate the cloud services, building a software system that is low-cost and scalable. The intention is *not* to simply create cloud resources \-- it is about the *integration* of these and therefore, correct configuration.

Remember, CAB432 is not really about software development: it is about computing in the cloud. Though, this assignment will require you to write more code than the previous.

Submission

You will submit one YAML file, submission-agent-infra.yml, following a structure like the one below.

The resources list should contain every cloud resource your solution depends on. The type field describes the kind of resource (for example, *Lambda function*, *S3 bucket*, *DynamoDB table*, or *Bedrock model*), while the arn field should contain the resource's unique identifier. This format is intentionally flexible and is not limited to AWS services. Each resource must also include a one-sentence plain-language description explaining its purpose in your solution.

Below is a sample. Add or remove as many resources as needed.

cloudInfrastructure:

  \- type: Bedrock model

    arn: \<model-id\>

    description: \<one-line description\>

  \- type: ECS service

    arn: \<arn\>

    description: \<one-line description\>

  \- type: Vector store

    arn: \<arn-or-other-identifier\>

    description: \<one-line description\>

  \- type: MCP server

    arn: \<arn-or-endpoint\>

    description: \<one-line description\>

  \- type: SQS queue

    arn: \<arn\>

    description: \<one-line description\>

  \- type: EventBridge rule

    arn: \<arn\>

    description: \<one-line description\>

  \- type: Secrets Manager secret

    arn: \<arn\>

    description: \<one-line description\>

  \- type: S3 bucket

    arn: \<arn\>

    description: \<one-line description\>

  \- type: DynamoDB table

    arn: \<arn\>

    description: \<one-line description\>

  \- type: Lambda function

    arn: \<arn\>

    description: \<one-line description\>

metaData:

  track: \<"A" | "B"\>

  qutUsernameTag: \<qut-username@qut.edu.au\>

Oral presentations

This is a Verified Identity Assessment (VIA). To maintain assessment integrity, teaching staff will verify your identity during the assessment. You will need to show your face and present your QUT ID Card or QUT Digital ID. If presenting online, you must keep your webcam on for the entire session and show your face. This process will be recorded. If you have any concerns, please contact your unit coordinator at least one week before the assessment date.

Read more here: [https://qutvirtual4.qut.edu.au/group/student/study/classes-and-readings/verified-identity-assessments](https://qutvirtual4.qut.edu.au/group/student/study/classes-and-readings/verified-identity-assessments)

Assignment 2 requires you to present your assignment to a CAB432 staff member. This is not a presentation to your peers. It will be a one-to-one session with a staff member. The maximum presentation time is 15 minutes.

You may present either online or in person at Gardens Point. All presentations will be recorded via Zoom. Regardless of where you present, you must join the Zoom meeting from the computer you are using for your demonstration.

