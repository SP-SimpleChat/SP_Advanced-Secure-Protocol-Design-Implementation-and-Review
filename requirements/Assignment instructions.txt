# Advanced Secure Protocol Design, Implementation and Review

This Advanced Secure Programming assignment is designed to help students apply the theoretical concepts covered in the lectures/RangeForce and learn about practice secure programming. This assignment is a group work assignment.  In groups of 3-5 students, you will engage in a hands-on assignment that requires the design, development, and evaluation of a secure overlay chat system utilising a standardised protocol created by all the students in this class. This system must adhere to class-specified protocol, have a secure implementation, have the secured implementation intentionally and ethically "backdoored", and then be tested in a controlled code review process. The course concludes with a friendly hackathon exercise.

 

## Assignment Objectives

Conceptualising and standardising a secure communication protocol for a distributed overlay multi-party chat system.
There cannot be any central server handling all the communication. Rather, the system must be robust to any node or device failure. 
Develop an application that adheres to a designed protocol (by the class) and incorporates advanced secure coding practices.  
Intentionally backdoor your own implementation in an ethical way so that other groups have security flaws to find. 
Perform peer reviews and engage in both manual and automated code analysis to identify vulnerabilities and backdoors.  
Critically reflect on the design and implementation process, including evaluating the protocol, the security measures implemented, the quality of the feedback received, a reflection on your own learning and possible coding mistakes.
Have fun at an ethical hackathon to identify and exploit vulnerabilities in a controlled setting, enhancing your understanding of real-world cybersecurity challenges.
 

## Assignment Timeline and Deliverables

Week 2: Complete the initial design of the chat system's communication protocol.
Week 4: Collaborative standardisation of the protocol with class-wide consensus.
Week 6: Finalise detailed plans for code design and start your implementation. 
Week 8: Present a functional prototype in the tutorial for initial testing and feedback.  Consider this as the deadline to finish your implementation. 
Week 9: Submit the final version of the chat system for peer review. HARD DEADLINE: 06 Oct 2025. If you submit after this day, your code won't be sent for peer review because it's unfair for your peers to receive late code for review.
Week 10: Conduct code reviews of three other groups' projects using both manual and automated code review techniques. Provide constructive feedback on the vulnerabilities found in peer reviews. DEADLINE for peer feedback: 19 Oct 2025.
Week 11: Submit a reflective commentary discussing the protocol standards, implementation challenges, thoughts on the embedded backdoors, and their detection difficulty.  Include in your submission the backdoor-free code and your backdoored code.  DEADLINE: 26 Oct 2025.
Week 12: Participate in a friendly, ethical hackathon to test all chat systems for vulnerabilities and demonstrate proof-of-concept attacks in a VM environment.

Participate in workshops to aid protocol development and refine implementation strategies.

 

## Programming and Implementation Details

Your group is free to use any programming language it feels comfortable with, such as C, Python, Rust, or any other suitable programming language. 

 

## Task Overview

The goal is to create a system that functions according to specified requirements and incorporates intentional vulnerabilities (backdoors) that peers will attempt to identify and exploit.  Your aim is to understand the trade-offs in protocol design at different levels with different objectives and problems. This develops critical thinking about aspects of protocols, programming, security, and vulnerabilities in code. 

In order to achieve that, we will design and secure our own protocol (as a whole class group). We will study this using the example of an overlay multi-party chat program. At the end of the module, we will have discussed and implemented a set of major Internet protocols, and you will have a program that must interwork with other students' programs to provide a chat service with:

Listing all members (currently online) in the chat system.
Private messages to a single participant: For example, your protocol is able to "forward" chat messages to the appropriate destination (according to your "routing table"), and the appropriate recipient displays the right chat messages.
Group messages to all participants. 
Point-to-point file transfer.
## What you need to consider is:

How to secure the socket from which you are receiving data.
Consider a malicious user using your program.
Consider malicious nodes participating in your protocol and/or a malicious actor "wiretapping" your communication.
While at the same time forwarding/routing messages through an overlay topology and securing the protocol communication. 
Consider core functionalities like user registration, and message sending/receiving (/w authentication). 
During the workshop session, you will design a protocol where you (the cohort of students) can work together to agree on a protocol that will be implemented within the chat program. You will then work in groups of 3-5 students to implement the protocol independently of the other groups. 

 

## Phase 1: Protocol Design (Weeks 1-4)

Objective: Design a standardised network protocol for a chat system that supports listing members, sending private and group messages, and conducting file transfers—a protocol specification document detailing all functional and security aspects agreed upon by all groups. 

Approach:

Weeks 1-2: Research existing secure communication protocols to understand foundational concepts. Begin drafting protocol specifications focusing on user authentication, data integrity, and encryption methods. Use the workshop during week 2 to communicate with your fellow students.  

Weeks 3-4: Standardise the protocol in collaboration with your peers in the whole class. Ensure it includes details on message formatting, session management, packet routing, error handling, and security measures.

 

## Phase 2: Software Implementation (Weeks 5-9)

Objective: Implement the agreed protocol that has been "standardised".  Note carefully that while the protocol specification needs to be the same for the whole class (otherwise, you will not be able to communicate with the implementation from other groups), your implementation is group-specific.  A working prototype of the chat system should be submitted by every group at the end.

Approach:

Weeks 5-6: Design the software architecture and start implementing it.  While you are still in the process of focusing on completing the last RangeForce modules, it is essential that by the workshop in week 6, you have a clear understanding of what to code.  You should use the session with your tutor to discuss any questions you might have. 

Weeks 7-8: These will be the main coding weeks. If you have a well-planned and standardised protocol, you will see that the actual implementation is not that hard. By the end of week 8, your code should really be finished.  See this as the deadline, so you have a few days to debug your code with other groups. 

Tutorial in Week 8: Present a working prototype for initial testing and informal feedback from other groups and tutors.

Week 9:  Finish debugging your code and add some backdoors (and/or vulnerabilities only known to your group) to the code. There must be at least 2 intentional vulnerabilities for the other groups to find.  Your friendly hackathon competition is to make it as hard for the other groups to find those hidden vulnerabilities. However, also keep in mind that ideally, you need to be able to exploit your own vulnerabilities and demonstrate later that you can achieve the objectives.

A hopefully obvious but important note on the intentional backdoors: The objectives are limited to within the chat system.  Do not include anything that would breach anything from the computer of the person who runs your code.  The idea is proof of concept, e.g., that you could take control of the running program, modify or alter messages on the node, sign with their private key, etc. However, keep it ethical.  Do not breach anyone's privacy or modify or delete any of the data outside of this assignment. 

On Monday in week 9, 06 Oct 2025: Submit your complete chat system (the version of your code with backdoors/vulnerabilities) for review by other groups. Submit on the MyUni assignment page: Submission of Implementation.  Your submission should have your (intentionally vulnerable) code and a detailed "README" (as ASCII) with instructions on compiling, running and using the code. 

 

## Phase 3: Testing and Peer Review (Week 10)

Objective: Conduct thorough testing and review of the chat system to identify planted and potential unintended vulnerabilities. Please submit a feedback review report outlining the vulnerabilities found and suggestions for improvement for the other groups.

Approach:

Week 10: Each student gets 3 implementations from other groups to review.  This is an individual sub-task in order to practice reviewing for every student and maximise the feedback others receive. You will use a combination of manual inspection and automated tools (e.g., static code analysis/dynamic analysis). Focus on identifying the intentional backdoors and any other security flaws left by other groups. However, it also provides detailed feedback to other groups, highlighting both strengths and vulnerabilities in their implementations.  Your feedback is expected to be returned to the other students no later than 19 October 2025. 

Note that you can, of course, share the feedback from the individual peer review task with your group members and overall make your code better as a group.  Feedback given will also be discussed in the reflective commentary as a group. 

While every group's backdoored code version is implemented ethically, always treat the code or produced binaries as if they were malicious. The code will certainly open ports to receive messages and will have intentional and/or unintentional vulnerabilities associated with it.  Run code received from other groups only in a sandboxed and secured environment!  It is essential to practice protecting yourself from malware and learning how to become a malware researcher, as the code you receive should only contain ethical backdoors, but nevertheless, make sure your own systems remain safe. 

 

## Phase 4: Reflection and Feedback (Week 11)

Objective: Reflect on the development process and learn from the feedback received.

Approach:

Write a reflective commentary discussing your protocol's standards, implementation challenges, thoughts on the integrated backdoors, and anticipated difficulty detecting them.  As guidance, do not write more than 2000 words (~4 pages single-spaced A4).  Your code, proof of concept, and screenshots can go to a set of appendices, which do not count into those 2000 words/4 pages. 

The reflective commentary should contain the following information:

Your reflection on the standardised protocol.  Even if you had to comply with the agreed implementation (in order to achieve interoperability), you might have had a different view.  Here is the space to comment and give your thoughts on what worked and what didn't work. 
Describe and submit your backdoor-free version of the code.  Explain design choices in the implementation.  Demonstrate how your code runs (by chatting with your own implementation or by chatting with other implementations).  Discuss lessons learned.  This can also include any bugs reported by other groups. 
Explain what backdoors/vulnerabilities you added.  What were your thoughts and objectives?.  Explain and demonstrate how to exploit your backdoor. 
Evaluate the feedback you received from other groups.  Did they find your backdoors?  Did they find other problems in your code?  Was the report useful feedback?  
For what groups did you provide feedback (name the group and group members).  What feedback did you provide to other groups?  What challenges did you face?  How did you overcome or approach those challenges (e.g., did you talk to the other groups)? 
 

## Phase 5: Ethical Hackathon (Week 12)

Objective: Test the security of all chat systems in a controlled, ethical environment.

Approach:

Participate in a hackathon where each group attempts to exploit vulnerabilities in others' systems. That means running your own vulnerable code in a VM (or otherwise safe environment).  Ethically, try to exploit others' code.  Use only non-destructive methods and aim to demonstrate proof of concept for potential attacks. All activities should be conducted on isolated virtual machines (VMs) to prevent any real-world implications.  
