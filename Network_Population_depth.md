# Adding depth to the network 
There should be access to a series of parameters that control the guardrails within which certain weights exists. For example:
- Pacific or aggressive city: if a city is more aggressive in nature, animosity will change by bigger leaps (so that for example riots or beatings from the guards increase). The opposite is true for a pacific city. 
- A religious city has an effect on the relationship with the priests. 
- A generally loyal city will have the guards taking less bribes, and the people be more respectful of the governing nobles, so animosity will increase a bit slower. 
- It would be cool if these parameters could be set as "dynamic". An example: if a city starts as very religious, but then there is a disease and many people die, animosity towards them will increase, evenmm slowly. This will make the city a bit less religious, which means that if there is another disease with similar effects, the animosity towards priests will change a bit faster. 
- Recommend other parameters if they come to mind, maybe checking the narrative gaps we have left behind. 
- A disease, or an external war, will make it so that the governing organ will increase taxes to everyone. Taxes increase animosity towards them. 
- People can be born! Family ties like grandpa, uncle, and nephew shuld exist. 
- Religiousness should be a property of people. 

## People
- People can fall in love. 
- If affinity is high enough between people (from both sides), they fall in love and get married. 
- From there, if they are opposite gender, they have kids.
- It is very unlikely for people from different classes to fall in love, but not impossible. 
- Affinity between people from different classes grows slowly. Animosity grows fast, depending on events. 


## Guards
- Guards are more or less public figures. They have a sort of connection with everyone in the city. The population might have animosity towards the guards because of certain events (guards increasing their beatings, increased taxes), or guards might have more animosity towards people (maybe they commited a crime, and are being searched for. Crime could be manslaughter or killing). Guards can either arrest people (low animosity), arrest them (high animosity), ignore them (high affinity), or can be bribed (mid affinity). 
- If the animosity of the poeple towards the guards becomes generally large, then there is a chance for riots. We have to find a realistic model for riots. 
- Guards can be bribed. Bribing a guard increases the affinity of them towards you. The price of a bribe is set by how rich the city is. 
- When guards are bribed by priests or nobles, their animosity towards people either attacking or stealing from them increases by a multiplying factor. It is not as if they were stealing from normal people. 
- Guards are already skewered towards having more affinity for nobles and more animosity towards poor people that do something to nobles. 
- If there is a governor, animosity towards them from the people trickles to the guards and the nobles as well. 

## Criminals
- Thieves should exist as an occupation. 
- If people are too poor, there is a chance they might become thieves. 
- Crimes then become manslaughet and theft. For every criminal event, there is a chance that the culprit is discovered. If they are, their relationship with the poeple around them and with the guards changes.
- Assassins are not always successfull. Even if they attempt a manslaughter, there should be a chance for the other person to survive. This makes the probability of the attempted murderer being discovered a 100% percent. If a poor person tries to kill a rich or noble person, the probability of success is lower.  
- If multiple people have similar animosity to the same individual, and high enough affinity between each other, they attempt the murder together. This increases the chances of the murder succeeding drastically. If enough band together, a riot is started. 

## Priests
- if the town is very religious, priests get a boost to their affinity with basically everyone. A few heretics or skeptics can be chosen within the city, for which instead animosity is boosted. 
- Priests can be corrupt (accept payments from the people for services and so on)
- Priests are the poeple that cure the diseases. If many people die from a disease, they are going to be seen as culpable --> increase in animosity. 
- If general religiousness is low, priests might bribe guards. 
- Priests start a quarantine if the disease is too contagious or too dangerous. 
- Priests and nobles can institute quarantine for dangerous diseases. This increases by a lot the chance of dying for people in the hit area, chance of survival or of not getting diseases for everyone else. It also increases the animosity of the general people towards whatever class, priests or nobles, chose to start the quarantine. 

## Nobles
- nobles and poor have animosity skewered towards lower values. The more riots and general discontent within the city (e.g. because of high taxes), the more this animosity increases, especially from the poor folks side. High general animosity has the same effect as with the guards --> riots. 
- Nobles start a quarantine if the initial center of infection is close enough to the rich areas, or if rich people start dying. If there is a governor, they get most of the anger from the people if this choice is made. 
- One or a few of the nobles should become the head figures of the city (if narrative allows for that). 
- Nobles can hire mercenaries to protect them. So can priests. How many they buy is affected by how the animosity towards nobles is. More personal guards (with a cap that makes reasonable sense) decrease the chance of success. 
- Nobles VERY RARELY commit manslaughter. If they want someone killed, they hire a mercenary assassin to do it. 
- Nobles never steal (for now). 
- Taxes increase animosity of nobles towards the governon. If animosity increases enough, nobles will try to hire mercenaries, to attack and kill the governing organ and become it themselves. 
- The more mercenaries are hired, the more the governing organ becomes suspicious, and there is a chance they might realize a coup is underway. 
- If animosity towards nobles raises too much, they can bribe the priests to talk well about them. The influence of the priests will lower animosity/increase affinity from poor people towards the nobles. The increase and decrease are proportional to the influenced person's religiousness. 

## Additional
- We should start adding a list of possible events. The ones I am thinking of are killing, stealing, loving, bribing, hiring, influencing, but there might be more hidden in what I have written above. Share your ideas on this with me. 
- Based on the events, we agree on what edges and weights affect them, and how. 
- People should have innate properties, like: religiousness, cunning, skepticism, loialty. All the properties influence the events involving these people (less or more likely to be bribed, to be succesfull in a murder, to become thieves, to start a riot...). Some of these properties should change based on events (e.g. if the guards beat a person, them or their close connection will not keep being as loyal). Global properties of the town are determined by local properties of the individuals. 