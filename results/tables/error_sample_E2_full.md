### 0. q1267 (thrombosis_prediction, moderate, conf 0.4)
Q: Among the patients with normal anti-SM, how many of them does not have thrombosis?
HINT (not shown to the agent): normal anti-SM refers to SM IN('-', '+-'); SM = 'negative' means '-'; SM = '0' means '+-'; SM = '1' means '+'; does not have thrombosis refers to Thrombosis = 0;
RETRIEVED DEFINITIONS: ['does not have any symptom refers to symptoms IS NULL', "normal anti-scl70 refers to SC170 IN('negative', '0')", 'thrombosis level 2 refers to Thrombosis = 2', "normal level of anti-SSB refers to SSB IN('-', '+-')", "the most serious thrombosis refers to Thrombosis = '1' (the most severe one)"]
GOLD: SELECT COUNT(T1.ID) FROM Examination AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.SM IN ('negative','0') AND T1.Thrombosis = 0
PRED: SELECT COUNT(DISTINCT T1.ID) 
FROM Patient AS T1 
INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID 
INNER JOIN Examination AS T3 ON T3.ID = T2.ID 
WHERE (T2.SM = 'negative' OR T2.SM = '0') AND T3.Thrombosis = 0
ERROR: None

### 1. q634 (codebase_community, challenging, conf 0.4)
Q: Among posts by Harvey Motulsky and Noah Snyder, which one has higher popularity?
HINT (not shown to the agent): Has higher popularity means the post has higher view count ; calculation = MAX(SUM(ViewCount)) where DisplayName = 'Harvey Motulsky' OR DisplayName = 'Noah Snyder';
RETRIEVED DEFINITIONS: ["DisplayName = 'Harvey Motulsky'", 'the most views refer to MAX(ViewCount)', "post by slashnick refers to DisplayName = 'slashnick'", '"Understanding what Dassault iSight is doing?" is the Title of post', 'user refers to UserId']
GOLD: SELECT T1.DisplayName FROM users AS T1 INNER JOIN postHistory AS T2 ON T1.Id = T2.UserId INNER JOIN posts AS T3 ON T2.PostId = T3.Id WHERE T1.DisplayName = 'Harvey Motulsky' OR T1.DisplayName = 'Noah Snyder' GROUP BY T1.DisplayName ORDER BY SUM(T3.ViewCount) DESC LIMIT 1
PRED: SELECT T2.Title, T2.ViewCount 
FROM users AS T1 
INNER JOIN posts AS T2 ON T1.Id = T2.OwnerUserId 
WHERE T1.DisplayName IN ('Harvey Motulsky', 'Noah Snyder') 
ORDER BY T2.ViewCount DESC 
LIMIT 1
ERROR: None

### 2. q1175 (thrombosis_prediction, moderate, conf 0.4)
Q: How old was the patient who had the highest hemoglobin count at the time of the examination, and what is the doctor's diagnosis?
HINT (not shown to the agent): How old the patient refers to SUBTRACT(year(`Examination Date`), year(Birthday)); the highest hemoglobin count refers to MAX(HGB)
RETRIEVED DEFINITIONS: ['The larger the birthday value, the younger the person is, and vice versa', 'normal hemoglobin level refers to 10 < HGB < 17', "diagnosed with SLE refers to Diagnosis = 'SLE'", "followed up at the outpatient clinic refers to Admission = '-'", "laboratory test in April 1981 refers to Date like '1991-10%'"]
GOLD: SELECT STRFTIME('%Y', T2.Date) - STRFTIME('%Y', T1.Birthday), T1.Diagnosis FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID ORDER BY T2.HGB DESC LIMIT 1
PRED: SELECT T1.Birthday, T1.Diagnosis 
FROM Patient AS T1 
INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID 
WHERE T2.HGB > 0 
ORDER BY T2.HGB DESC 
LIMIT 1
ERROR: None

### 3. q1387 (student_club, moderate, conf 0.2)
Q: Which student has been entrusted to manage the budget for the Yearly Kickoff?
HINT (not shown to the agent): name of students means the full name; full name refers to first_name, last_name;'Yearly Kickoff' is an event name;
RETRIEVED DEFINITIONS: ["'President' is a position of Student Club", "'Vice President' is a position of Student Club", "percentage = DIVIDE(SUM(cost where event_name = 'Yearly Kickoff'), SUM(cost)) * 100", 'budget category refers to category', '0 budget spent refers to spent = 0']
GOLD: SELECT T4.first_name, T4.last_name FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event INNER JOIN expense AS T3 ON T2.budget_id = T3.link_to_budget INNER JOIN member AS T4 ON T3.link_to_member = T4.member_id WHERE T1.event_name = 'Yearly Kickoff'
PRED: SELECT T3.first_name, T3.last_name 
FROM event AS T1 
INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event 
INNER JOIN member AS T3 ON T2.link_to_event = T3.link_to_major 
WHERE T1.event_name = 'Yearly Kickoff'
ERROR: None

### 4. q687 (codebase_community, simple, conf 0.4)
Q: How many comments were added to the post with the highest score?
HINT (not shown to the agent): the highest score refers to MAX(Score);
RETRIEVED DEFINITIONS: ['comment with the highest score refers to Text where MAX(Score)', 'views ranging from 100 to 150 refers to ViewCount BETWEEN 100 and 150', 'contents of comments refers to Text', 'score of 17 refers to Score = 17', "user no. 24 refers to UserId = OwnerUserId = '24'"]
GOLD: SELECT COUNT(T2.Id) FROM posts AS T1 INNER JOIN comments AS T2 ON T1.Id = T2.PostId GROUP BY T1.Id ORDER BY T1.Score DESC LIMIT 1
PRED: SELECT COUNT(*) 
FROM posts p
JOIN comments c ON p.Id = c.PostId
JOIN postHistory ph ON p.Id = ph.PostId
WHERE p.Score = (SELECT MAX(Score) FROM posts)
AND ph.Comment = 'added'
ERROR: None

### 5. q37 (california_schools, moderate, conf 0.6)
Q: What is the complete address of the school with the lowest excellence rate? Indicate the Street, City, Zip and State.
HINT (not shown to the agent): Execellence Rate = NumGE1500 / NumTstTakr; complete address has Street, City, State, Zip code
RETRIEVED DEFINITIONS: ['Full communication address should include Street, City, State and zip code if any', 'Excellence rate = NumGE1500 / NumTstTakr', "State Special School means EdOpsCode = 'SSS'", 'Eligible free rates for students aged 5-17 = `Free Meal Count (Ages 5-17)` / `Enrollment (Ages 5-17)`', 'Grades 1 through 12 means K-12']
GOLD: SELECT T2.Street, T2.City, T2.State, T2.Zip FROM satscores AS T1 INNER JOIN schools AS T2 ON T1.cds = T2.CDSCode ORDER BY CAST(T1.NumGE1500 AS REAL) / T1.NumTstTakr ASC LIMIT 1
PRED: SELECT 
    T2.Street, 
    T2.City, 
    T2.Zip, 
    T2.State 
FROM 
    satscores AS T1 
INNER JOIN 
    schools AS T2 
ON 
    T1.cds = T2.CDSCode 
ORDER BY 
    CAST(T1.NumGE1500 AS REAL) / T1.NumTstTakr ASC 
LIMIT 1
ERROR: None

### 6. q408 (card_games, moderate, conf 0.4)
Q: How many unknown power cards contain info about the triggered ability
HINT (not shown to the agent): unknown power cards refers to power is null or power = '*';contain info about the triggered ability refers to text contains 'triggered ability'
RETRIEVED DEFINITIONS: ["unknown power refers to power = '*' or POWER IS NULL", "commander play format refers to format = 'commander'", "the percentage of incredibly powerful cards in the set refers to DIVIDE(SUM(incredibly powerful), SUM(name = 'Coldsnap'))*100", "legal for commander play format refers to format = 'commander' where status = 'Legal'", 'set of 180 cards refers to baseSetSize = 180']
GOLD: SELECT Count(DISTINCT T1.id) FROM cards AS T1 INNER JOIN rulings AS T2 ON T1.uuid = T2.uuid WHERE (T1.power IS NULL OR T1.power = '*') AND T2.text LIKE '%triggered ability%'
PRED: SELECT COUNT(*) FROM cards WHERE (power IS NULL OR power = '*') AND text LIKE '%Triggered Ability%'
ERROR: None

### 7. q894 (formula_1, moderate, conf 0.2)
Q: What is the best lap time recorded? List the driver and race with such recorded lap time.
HINT (not shown to the agent): the best lap time refers to min(milliseconds); List the driver refers to drivers.forename and drivers.surname; List the race refers to races.name
RETRIEVED DEFINITIONS: ['Only the time of the champion shows in the format of "hour: minutes: seconds.millionsecond"', 'Full name of the driver refers to drivers.forename and drivers.surname', 'the fastest lap speed refers to (MAX) fastestLapSpeed', 'Lewis Hamiltonrefers to the full name of the driver', 'fastest lap refers to min(milliseconds)']
GOLD: SELECT T2.milliseconds, T1.forename, T1.surname, T3.name FROM drivers AS T1 INNER JOIN lapTimes AS T2 ON T1.driverId = T2.driverId INNER JOIN races AS T3 ON T2.raceId = T3.raceId ORDER BY T2.milliseconds ASC LIMIT 1
PRED: SELECT T3.forename || ' ' || T3.surname AS DriverName, T1.name AS RaceName, T1.year AS Year, MIN(T2.milliseconds) AS BestLapTime
FROM races AS T1
INNER JOIN lapTimes AS T2 ON T2.raceId = T1.raceId
INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId
WHERE T3.forename = 'Lewis' AND T3.surname = 'Hamilton'
ERROR: None

### 8. q869 (formula_1, moderate, conf 0.8)
Q: For the constructor which got the highest point in the race No. 9 , what is its introduction website?
HINT (not shown to the agent): race number refers to raceId; constructor which got the highest point refers to MAX(constructorResults.points); introduction website of the constructor refers to url;
RETRIEVED DEFINITIONS: ['introduction website of the drivers refers to url', 'rank the highest refers to min(rank)', "'Lewis Hamilton' refers to the full name of the driver", 'player and driver are synonyms', 'race at 291 refers to raceID = 291']
GOLD: SELECT T2.url FROM constructorResults AS T1 INNER JOIN constructors AS T2 ON T2.constructorId = T1.constructorId WHERE T1.raceId = 9 ORDER BY T1.points DESC LIMIT 1
PRED: SELECT T2.url 
FROM constructorStandings AS T1 
INNER JOIN constructors AS T2 
ON T1.constructorId = T2.constructorId 
WHERE T1.raceId = 9 
ORDER BY T1.points DESC 
LIMIT 1
ERROR: None

### 9. q672 (codebase_community, moderate, conf 0.4)
Q: Among the users located in United Kingdom, how many users whose post have a total favorite amount of 4 or more?
HINT (not shown to the agent): favorite amount of 4 or more refers to FavoriteCount > = 4; Location = 'United Kingdom';
RETRIEVED DEFINITIONS: ['creating more than 10 post refers to Count (UserId) > 10', 'times of his/her post than votes = Divide (Count(post.Id), Count(votes.Id))', 'average age = Divide (Sum(Age), Count(UserId))', "user no. 24 refers to UserId = OwnerUserId = '24'", 'user refers to UserId']
GOLD: SELECT COUNT(T1.Id) FROM users AS T1 INNER JOIN posts AS T2 ON T1.Id = T2.OwnerUserId WHERE T1.Location = 'United Kingdom' AND T2.FavoriteCount >= 4
PRED: SELECT COUNT(DISTINCT u.Id) 
FROM users u
JOIN posts p ON u.Id = p.OwnerUserId
WHERE u.Location = 'United Kingdom'
GROUP BY u.Id
HAVING SUM(p.FavoriteCount) >= 4
ERROR: None

### 10. q1473 (debit_card_specializing, moderate, conf 1.0)
Q: What was the average monthly consumption of customers in SME for the year 2013?
HINT (not shown to the agent): Average Monthly consumption = AVG(Consumption) / 12; Year 2013 can be presented as Between 201301 And 201312; The first 4 strings of the Date values in the yearmonth table can represent year.
RETRIEVED DEFINITIONS: ['Increase or Decrease = consumption for 2013 - consumption for 2012', 'The 5th and 6th string of the date can refer to month', 'Percentage of Increase = (Increase or Decrease / consumption for 2013) * 100%', 'Difference in Consumption = CZK customers consumption in 2012 - EUR customers consumption in 2012', 'Year 2012 can be presented as Between 201201 And 201212']
GOLD: SELECT AVG(T2.Consumption) / 12 FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE SUBSTR(T2.Date, 1, 4) = '2013' AND T1.Segment = 'SME'
PRED: SELECT AVG(T2.Consumption) 
FROM customers AS T1 
INNER JOIN yearmonth AS T2 
ON T1.CustomerID = T2.CustomerID 
WHERE T1.Segment = 'SME' AND T2.Date BETWEEN '201301' AND '201312'
ERROR: None

### 11. q1201 (thrombosis_prediction, moderate, conf 0.8)
Q: What percentage of patients who were born in 1980 and were diagnosed with RA are women?
HINT (not shown to the agent): born in 1980 refers to YEAR(BIRTHDAY) = '1980'; 'RA' refers to Diagnosis='RA' ; women refers to SEX = 'F'; calculation = DIVIDE(SUM(SEX = 'F'), COUNT(SEX)) * 100
RETRIEVED DEFINITIONS: ["patient who were born after 1930 refers to year(Birthday) > '1930'", "female refers to Sex = 'F'", "calculation = DIVIDE(COUNT(ID) where year(Birthday) > '1930' and SEX = 'F'), (COUNT(ID) where SEX = 'F')", 'The larger the birthday value, the younger the person is, and vice versa', "diagnosed with SLE refers to Diagnosis = 'SLE'"]
GOLD: SELECT CAST(SUM(CASE WHEN SEX = 'F' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(ID) FROM Patient WHERE Diagnosis = 'RA' AND STRFTIME('%Y', Birthday) = '1980'
PRED: SELECT CAST(SUM(CASE WHEN T1.SEX = 'F' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM Patient AS T1 
INNER JOIN Examination AS T2 ON T1.ID = T2.ID 
WHERE STRFTIME('%Y', T1.Birthday) = '1980' AND T2.Diagnosis = 'RA'
ERROR: None

### 12. q1255 (thrombosis_prediction, moderate, conf 0.2)
Q: For the patients with an abnormal Ig M level, what is the most common disease they are diagnosed with?
HINT (not shown to the agent): abnormal Ig M level refers to IGM <=40 OR IGM >= 400; most common disease refers to MAX(COUNT(Diagnosis));
RETRIEVED DEFINITIONS: ['average anti-Cardiolip in antibody (IgM) refers to AVG(`aCL IgM`)', 'Ig G higher than normal refers to IGG >= 2000', 'Should consider DISTINCT in the final result', 'disease refers to diagnosis', 'abnormal platelet level refers to PLT <= 100 or PLT >= 400']
GOLD: SELECT T1.Diagnosis FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.IGM NOT BETWEEN 40 AND 400 GROUP BY T1.Diagnosis ORDER BY COUNT(T1.Diagnosis) DESC LIMIT 1
PRED: SELECT T3.Diagnosis 
FROM Patient AS T1 
INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID 
INNER JOIN Examination AS T3 ON T3.ID = T2.ID 
WHERE T3.`aCL IgM` < 0.4 OR T3.`aCL IgM` > 4.6 
GROUP BY T3.Diagnosis 
ORDER BY COUNT(T3.Diagnosis) DESC 
LIMIT 1
ERROR: None

### 13. q479 (card_games, moderate, conf 0.6)
Q: Among the cards with converted mana cost higher than 5 in the set Coldsnap, how many of them have unknown power?
HINT (not shown to the agent): card set Coldsnap refers to name = 'Coldsnap'; converted mana cost higher than 5 refers to convertedManaCost > 5; unknown power refers to power = '*' or T1.power is null
RETRIEVED DEFINITIONS: ['converted mana cost of 7 refers to convertedManaCost = 7', 'highest converted mana cost refers to MAX(convertedManaCost)', 'percentage = DIVIDE(SUM(convertedManaCost = 7), SUM(convertedManaCost))*100', "card set Coldsnap refers to name = 'Coldsnap'", "the percentage of incredibly powerful cards in the set refers to DIVIDE(SUM(incredibly powerful), SUM(name = 'Coldsnap'))*100"]
GOLD: SELECT SUM(CASE WHEN T1.power = '*' OR T1.power IS NULL THEN 1 ELSE 0 END) FROM cards AS T1 INNER JOIN sets AS T2 ON T2.code = T1.setCode WHERE T2.name = 'Coldsnap' AND T1.convertedManaCost > 5
PRED: SELECT COUNT(*) 
FROM cards AS T1 
INNER JOIN sets AS T2 ON T2.code = T1.setCode 
WHERE T2.name = 'Coldsnap' AND T1.convertedManaCost > 5 AND T1.power = '*'
ERROR: None

### 14. q861 (formula_1, simple, conf 1.0)
Q: What is his number of the driver who finished 0:01:54 in the Q3 of qualifying race No.903?
HINT (not shown to the agent): race number refers to raceId; finished 0:0M:SS in the Q3 refers to q3 LIKE 'M:SS%'
RETRIEVED DEFINITIONS: ['introduction website of the drivers refers to url', 'race number refers to raceId', 'second qualifying period refers to q2', 'Bruno Senna refers to the full name of the driver', 'COUNT(raceID) > 0 reveals that this driver participated in races']
GOLD: SELECT T2.number FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 903 AND T1.q3 LIKE '1:54%'
PRED: SELECT T2.number 
FROM qualifying AS T1 
INNER JOIN drivers AS T2 
ON T1.driverId = T2.driverId 
WHERE T1.raceId = 903 AND T1.q3 = '0:01:54'
ERROR: None

### 15. q586 (codebase_community, challenging, conf 0.4)
Q: Which user added a bounty amount of 50 to the post title mentioning variance?
HINT (not shown to the agent): bounty amount of 50 refers to BountyAmount = 50; user refers to DisplayName; title mentioning variance refers to Title include 'variance'
RETRIEVED DEFINITIONS: ['"Eliciting priors from experts" is the Title of post', "'Open source tools for visualizing multi-dimensional data' is the Title of Post", '"Why square the difference instead of taking the absolute value in standard deviation?" is the Title of post', 'The higher reputation the user has the more influence', 'percentage = DIVIDE(COUNT(stats_posts.Id where Score > 50 and MAX(Reputation))), COUNT(stats_posts.Id where MAX(Reputation))']
GOLD: SELECT T3.DisplayName, T1.Title FROM posts AS T1 INNER JOIN votes AS T2 ON T1.Id = T2.PostId INNER JOIN users AS T3 ON T3.Id = T2.UserId WHERE T2.BountyAmount = 50 AND T1.Title LIKE '%variance%'
PRED: SELECT T3.DisplayName 
FROM posts AS T1 
INNER JOIN votes AS T2 
ON T1.Id = T2.PostId 
INNER JOIN users AS T3 
ON T2.UserId = T3.Id 
WHERE T1.Title LIKE '%variance%' AND T2.BountyAmount = 50
ERROR: None

### 16. q978 (formula_1, simple, conf 0.6)
Q: How many times the circuits were held in Austria? Please give their location and coordinates.
HINT (not shown to the agent): location coordinates refers to (lat,lng); Austria refers to country = 'Austria';
RETRIEVED DEFINITIONS: ['Germany is a name of country', 'coordinate position/location refers to lat, lng', "circuits for Australian grand prix refers to races.name = 'Australian Grand Prix'", 'Netherlandic and Dutch refer to the same country', 'raceId > 50 and raceId < 100']
GOLD: SELECT DISTINCT location, lat, lng FROM circuits WHERE country = 'Austria'
PRED: SELECT COUNT(DISTINCT T2.circuitId), T1.location, T1.lat, T1.lng 
FROM circuits AS T1 
INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId 
WHERE T1.country = 'Austria'
ERROR: None

### 17. q1392 (student_club, simple, conf 0.8)
Q: Indicate the top source of funds received in September 2019 based on their amount.
HINT (not shown to the agent): top source funds refers to MAX(source); September 2019 means date_received BETWEEN '2019-09-01' and '2019-09-30'
RETRIEVED DEFINITIONS: ["fundraising on 2019/9/14 refers to source = 'Fundraising' where date_received = '2019-09-14'", "date the dues was paid refers to date_received where source = 'Dues'", 'budget categories refers to category', 'The first 4 strings of the event_date values in the event table can represent year', 'amount budgeted refers to SUM(amount)']
GOLD: SELECT source FROM income WHERE date_received BETWEEN '2019-09-01' and '2019-09-30' ORDER BY source DESC LIMIT 1
PRED: SELECT source, SUM(amount) AS total_amount 
FROM income 
WHERE date_received LIKE '2019-09%' 
GROUP BY source 
ORDER BY total_amount DESC 
LIMIT 1
ERROR: None

### 18. q281 (toxicology, challenging, conf 0.6)
Q: Tally the toxicology element of the 4th atom of each molecule that was carcinogenic.
HINT (not shown to the agent): label = '+' means molecules are carcinogenic; 4th atom of each molecule refers to substr(atom_id, 7, 1) = '4'; 
RETRIEVED DEFINITIONS: ["atoms from 21 to 25 refers to SUBSTR(atom_id, 7, 2) between '21' and '25'", "label = '-' means molecules are non-carcinogenic", "label = '+' mean molecules are carcinogenic", 'majority of the bond found refers to MAX(COUNT(bond_type))', 'least numerous refers to MIN(COUNT(element))']
GOLD: SELECT DISTINCT T1.element FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = '+' AND SUBSTR(T1.atom_id, -1) = '4' AND LENGTH(T1.atom_id) = 7
PRED: SELECT T1.element, COUNT(*) 
FROM atom AS T1 
INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id 
WHERE SUBSTR(T1.atom_id, 7, 2) = '04' AND T2.label = '+' 
GROUP BY T1.element
ERROR: None

### 19. q892 (formula_1, moderate, conf 1.0)
Q: State the driver with the most points scored. Find his full name with that points.
HINT (not shown to the agent): the most points scored refers to max(points); Full name of the driver refers to drivers.forename and drivers.surname;
RETRIEVED DEFINITIONS: ['average point scores refers to MAX(points)', 'the most winning refers to MAX(COUNT(wins))', 'Full name of the driver refers to drivers.forename and drivers.surname', 'player and driver are synonyms', 'List the race refers to races.name']
GOLD: SELECT T3.forename, T3.surname, T2.points FROM races AS T1 INNER JOIN driverStandings AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId ORDER BY T2.points DESC LIMIT 1
PRED: SELECT T1.forename, T1.surname, SUM(T2.points) AS total_points 
FROM drivers AS T1 
INNER JOIN results AS T2 
ON T1.driverId = T2.driverId 
GROUP BY T1.driverId 
ORDER BY total_points DESC 
LIMIT 1
ERROR: None

### 20. q169 (financial, challenging, conf 0.6)
Q: What was the growth rate of the total amount of loans across all accounts for a male client between 1996 and 1997?
HINT (not shown to the agent): Growth rate = (sum of amount_1997 - sum of amount_1996) / (sum of amount_1996) * 100%; Male refers to gender = 'M'
RETRIEVED DEFINITIONS: ['Increase rate of his/her account balance = [(balance of date A - balance of date B) / balance of Date B] * 100%', "January 1996 can be found by date LIKE '1996-01%' in the database", 'Percentage of accounts by condition = [(total(amount) & condition) / (total amount)] * 100%', "when the account type = 'OWNER', it's eligible for loans", "Status = 'C' stands for running contract, ok so far"]
GOLD: SELECT CAST((SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1997' THEN T1.amount ELSE 0 END) - SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1996' THEN T1.amount ELSE 0 END)) AS REAL) * 100 / SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1996' THEN T1.amount ELSE 0 END) FROM loan AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id INNER JOIN disp AS T3 ON T3.account_id = T2.account_id INNER JOIN client AS T4 ON T4.client_id = T3.client_id WHERE T4.gender = 'M' AND T3.type = 'OWNER'
PRED: SELECT CAST((SUM(CASE WHEN T1.`date` BETWEEN '1997-01-01' AND '1997-12-31' THEN T1.amount ELSE 0 END) - 
          SUM(CASE WHEN T1.`date` BETWEEN '1996-01-01' AND '1996-12-31' THEN T1.amount ELSE 0 END)) AS REAL) * 100 /
       SUM(CASE WHEN T1.`date` BETWEEN '1996-01-01' AND '1996-12-31' THEN T1.amount ELSE 0 END) AS growth_rate
FROM loan AS T1
INNER JOIN account AS T2 ON T1.account_id = T2.account_id
INNER JOIN disp AS T3 ON T2.account_id = T3.account_id
INNER JOIN client AS T4 ON T3.client_id = T4.client_id
WHERE T4.gender = 'M'
ERROR: None

### 21. q465 (card_games, moderate, conf 0.4)
Q: For the set of cards with "Ancestor's Chosen" in it, is there a Korean version of it?
HINT (not shown to the agent): set of cards with "Ancestor''s Chosen" in it refers to name = 'Ancestor''s Chosen'; Korean version refers to language = 'Korean'
RETRIEVED DEFINITIONS: ['with "Ancestor\'s Chosen" in the card set refers to name = \'Ancestor\'\'s Chosen\'', "Italian is a language which refers to language = 'Italian'", 'have a translation means translation is not null', "card does not have multiple faces on the same card refers to side is NULL'; vintage play format refers to format = 'vintage'", "available in paper and mtgo refers to availability = 'mtgo,paper'"]
GOLD: SELECT IIF(SUM(CASE WHEN T2.language = 'Korean' AND T2.translation IS NOT NULL THEN 1 ELSE 0 END) > 0, 'YES', 'NO') FROM cards AS T1 INNER JOIN set_translations AS T2 ON T2.setCode = T1.setCode WHERE T1.name = 'Ancestor''s Chosen'
PRED: SELECT CASE WHEN COUNT(*) > 0 THEN 'Yes' ELSE 'No' END AS has_korean_translation
FROM foreign_data
JOIN cards ON foreign_data.uuid = cards.uuid
WHERE cards.name = 'Ancestor''s Chosen' AND foreign_data.language = 'Korean'
ERROR: None

### 22. q1405 (student_club, moderate, conf 0.6)
Q: Calculate the amount budgeted for 'April Speaker' event. List all the budgeted categories for said event in an ascending order based on their amount budgeted.
HINT (not shown to the agent): 'April Speaker' is an event name; amount budgeted refers to SUM(amount); budget categories refers to category
RETRIEVED DEFINITIONS: ["'September Speaker' is an event name", 'highest amount of budget spend refers to MAX(spent)', "percentage = DIVIDE(SUM(cost where event_name = 'Yearly Kickoff'), SUM(cost)) * 100", "'Posters' is the expense description", 'highest spend-to budget ratio refers to MAX(DIVIDE(spent, amount))']
GOLD: SELECT T2.category, SUM(T2.amount) FROM event AS T1 JOIN budget AS T2 ON T1.event_id = T2.link_to_event WHERE T1.event_name = 'April Speaker' GROUP BY T2.category ORDER BY SUM(T2.amount) ASC
PRED: SELECT T2.amount, T2.category 
FROM event AS T1 
INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event 
WHERE T1.event_name = 'April Speaker' 
ORDER BY T2.amount ASC
ERROR: None

### 23. q1168 (thrombosis_prediction, challenging, conf 0.2)
Q: The oldest SJS patient's medical laboratory work was completed on what date, and what age was the patient when they initially arrived at the hospital?
HINT (not shown to the agent): The larger the birthday value, the younger the person is, and vice versa; 'SJS' refers to diagnosis; (SUBTRACT(year(`First Date`)), year(Birthday)); age of the patients when they initially arrived at the hospital refers to year(Birthday)
RETRIEVED DEFINITIONS: ['The larger the birthday value, the younger the person is, and vice versa', "laboratory test in April 1981 refers to Date like '1991-10%'", "came at the hospital in 1997 refers to year(Description) = '1997'", "'30609' is the Patient ID", "followed up at the outpatient clinic refers to Admission = '-'"]
GOLD: SELECT T1.Date, STRFTIME('%Y', T2.`First Date`) - STRFTIME('%Y', T2.Birthday),T2.Birthday FROM Laboratory AS T1 INNER JOIN Patient AS T2 ON T1.ID = T2.ID WHERE T2.Diagnosis = 'SJS' AND T2.Birthday IS NOT NULL ORDER BY T2.Birthday ASC LIMIT 1
PRED: SELECT 
    T2.Date AS LabCompletionDate,
    STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) AS AgeAtHospitalEntry
FROM 
    Patient AS T1
INNER JOIN 
    Laboratory AS T2 ON T1.ID = T2.ID
WHERE 
    T1.Diagnosis = 'SJS'
ORDER BY 
    T2.Date ASC
LIMIT 1
ERROR: None

### 24. q89 (financial, moderate, conf 1.0)
Q: How many accounts who choose issuance after transaction are staying in East Bohemia region?
HINT (not shown to the agent): A3 contains the data of region; 'POPLATEK PO OBRATU' represents for 'issuance after transaction'.
RETRIEVED DEFINITIONS: ['Accounts holder refers to the person who own this account', "Status = 'C' stands for running contract, ok so far", "Status = 'D' stands for running contract, client in debt", "'POPLATEK TYDNE' stands for weekly issuance", "Operation = 'VYBER KARTOU' refers to credit card withdrawal"]
GOLD: SELECT COUNT(T2.account_id) FROM district AS T1 INNER JOIN account AS T2 ON T1.district_id = T2.district_id WHERE T1.A3 = 'east Bohemia' AND T2.frequency = 'POPLATEK PO OBRATU'
PRED: SELECT COUNT(DISTINCT T1.account_id)
FROM account AS T1
INNER JOIN district AS T2 ON T1.district_id = T2.district_id
INNER JOIN disp AS T3 ON T1.account_id = T3.account_id
WHERE T2.A3 = 'east Bohemia'
AND T3.type = 'OWNER'
AND EXISTS (
    SELECT 1
    FROM trans AS T4
    WHERE T4.account_id = T1.account_id
    AND T4.operation = 'VYBER KARTOU'
)
ERROR: None

### 25. q1014 (formula_1, challenging, conf 0.6)
Q: Please list the lap records for the circuits in Italy.
HINT (not shown to the agent): lap record means the fastest time recorded which refers to time
RETRIEVED DEFINITIONS: ['Germany is a name of country', "circuits for Australian grand prix refers to races.name = 'Australian Grand Prix'", 'in 2009 refers to year = 2009', "Full name of the driver refers to drivers.forename ='Paul' and drivers.surname = 'di Resta'", "Spanish Grand Prix refers to races.name = 'Spanish Grand Prix'"]
GOLD: WITH fastest_lap_times AS (SELECT T1.raceId, T1.FastestLapTime, (CAST(SUBSTR(T1.FastestLapTime, 1, INSTR(T1.FastestLapTime, ':') - 1) AS REAL) * 60) + (CAST(SUBSTR(T1.FastestLapTime, INSTR(T1.FastestLapTime, ':') + 1, INSTR(T1.FastestLapTime, '.') - INSTR(T1.FastestLapTime, ':') - 1) AS REAL)) + (CAST(SUBSTR(T1.FastestLapTime, INSTR(T1.FastestLapTime, '.') + 1) AS REAL) / 1000) as time_in_seconds FROM results AS T1 WHERE T1.FastestLapTime IS NOT NULL ) SELECT T1.FastestLapTime as lap_record FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN circuits AS T3 on T2.circuitId = T3.circuitId INNER JOIN (SELECT MIN(fastest_lap_times.time_in_seconds) as min_time_in_seconds FROM fastest_lap_times INNER JOIN races AS T2 on fastest_lap_times.raceId = T2.raceId INNER JOIN circuits AS T3 on T2.circuitId = T3.circuitId WHERE T3.country = 'Italy' ) AS T4 ON (CAST(SUBSTR(T1.FastestLapTime, 1, INSTR(T1.FastestLapTime, ':') - 1) AS REAL) * 60) + (CAST(SUBSTR(T1.FastestLapTime, INSTR(T1.FastestLapTime, ':') + 1, INSTR(T1.FastestLapTime, '.') - INSTR(T1.FastestLapTime, ':') - 1) AS REAL)) + (CAST(SUBSTR(T1.FastestLapTime, INSTR(T1.FastestLapTime, '.') + 1) AS REAL) / 1000) = T4.min_time_in_seconds LIMIT 1
PRED: SELECT T2.lap, T2.position, T2.time 
FROM circuits AS T1 
INNER JOIN races AS T3 ON T1.circuitId = T3.circuitId
INNER JOIN lapTimes AS T2 ON T3.raceId = T2.raceId 
WHERE T1.country = 'Italy'
ERROR: None

### 26. q1235 (thrombosis_prediction, moderate, conf 0.8)
Q: What are the patient's diagnosis for those who has lower red blood blood cell? State their ID and age.
HINT (not shown to the agent): patient's diagnosis refers to Diagnosis; lower red blood cell refers to RBC < 3.5; age = SUBTRACT(year(current_timestamp), year(Birthday)); 
RETRIEVED DEFINITIONS: ['The larger the birthday value, the younger the person is, and vice versa', 'age refers to SUBTRACT(year(current_timestamp), year(Birthday))', 'patient with two or more laboratory examinations refers to COUNT(ID) > 2', 'age = SUBTRACT(year(current_timestamp), year(Birthday))', "diagnosed with SLE refers to Diagnosis = 'SLE'"]
GOLD: SELECT DISTINCT T1.Diagnosis, T1.ID , STRFTIME('%Y', CURRENT_TIMESTAMP) -STRFTIME('%Y', T1.Birthday) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.RBC < 3.5
PRED: SELECT T1.ID, STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) AS Age, T1.Diagnosis 
FROM Patient AS T1 
INNER JOIN Laboratory AS T2 
ON T1.ID = T2.ID 
WHERE T2.RBC < 3.5
ERROR: None

### 27. q405 (card_games, moderate, conf 0.8)
Q: How many Brazilian Portuguese translated sets are inside the Commander block?
HINT (not shown to the agent): Commander block refer to block = 'Commander'; sets refer to code = setCode; Portuguese refer to language = 'Portuguese (Brasil)'
RETRIEVED DEFINITIONS: ['set of 180 cards refers to baseSetSize = 180', "commander play format refers to format = 'commander'", "having the code ARC refers to setCode = 'ARC'", "legal for commander play format refers to format = 'commander' where status = 'Legal'", "known as Archenemy refers to mcmName = 'Archenemy'"]
GOLD: SELECT COUNT(T1.id) FROM sets AS T1 INNER JOIN set_translations AS T2 ON T1.code = T2.setCode WHERE T2.language = 'Portuguese (Brazil)' AND T1.block = 'Commander'
PRED: SELECT COUNT(DISTINCT T1.name) 
FROM sets AS T1 
INNER JOIN set_translations AS T2 ON T1.code = T2.setCode 
WHERE T1.block = 'Commander' AND T1.type = 'commander' AND T2.language = 'Brazilian Portuguese'
ERROR: None

### 28. q906 (formula_1, moderate, conf 0.4)
Q: Which was Lewis Hamilton first race? What was his points recorded for his first race event?
HINT (not shown to the agent): first race refers to min(Year); Lewis Hamiltonrefers to the full name of the driver; Full name of the driver refers to drivers.forename and drivers.surname;
RETRIEVED DEFINITIONS: ["'Lewis Hamilton' refers to the full name of the driver", 'first qualifying race refers to MIN(races.date)', 'rank the highest refers to min(rank)', "percentage = DIVIDE(COUNT(raceId) where surname = 'Hamilton' and position>1), (COUNT(raceId) where surname = 'Hamilton')", 'Full name of the driver refers to drivers.forename and drivers.surname']
GOLD: SELECT T1.name, T2.points FROM races AS T1 INNER JOIN driverStandings AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.forename = 'Lewis' AND T3.surname = 'Hamilton' ORDER BY T1.year ASC LIMIT 1
PRED: SELECT T3.name AS RaceName, T2.points AS PointsRecorded 
FROM drivers AS T1 
JOIN results AS T2 ON T1.driverId = T2.driverId 
JOIN races AS T3 ON T2.raceId = T3.raceId 
WHERE T1.surname = 'Hamilton' 
ORDER BY T3.date ASC 
LIMIT 1
ERROR: None

### 29. q1135 (european_football_2, moderate, conf 1.0)
Q: Please provide top four football players' IDs who are among the lowest potential players and prefer to use the right foot when attacking.
HINT (not shown to the agent): lowest potential players refers to MIN(potential); prefer to use the right foot when attacking refers to preferred_foot = 'right'
RETRIEVED DEFINITIONS: ["preferred to use their left foots while attacking refers to preferred_foot = 'left'", "players who prefer left foot refers to preferred_foot = 'left'", 'highest potential score for crossing refers to MAX(crossing)', "percentage of players who prefer left foot = DIVIDE(MULTIPLY((SUM(preferred_foot = 'left'), 100)), COUNT(player_fifa_api_id))", "born between 1987 and 1992 refers to YEAR(birthday) BETWEEN '1987' AND '1992'"]
GOLD: SELECT id FROM Player_Attributes WHERE preferred_foot = 'right' ORDER BY potential ASC LIMIT 4
PRED: SELECT player_api_id 
FROM Player_Attributes 
WHERE preferred_foot = 'right' 
ORDER BY potential ASC 
LIMIT 4
ERROR: None

### 30. q1243 (thrombosis_prediction, challenging, conf 0.4)
Q: For all patients who are older than 55 years old, what is the percentage of female who has abnormal prothrombin time (PT)?
HINT (not shown to the agent): older than 55 years old = SUBTRACT(year(current_timestamp), year(Birthday)) > 55; abnormal prothrombin time (PT) refers to PT > = 14; percentage = DIVIDE(SUM(PT > = 14 AND SEX = 'F'), SUM(PT > = 14)) * 100; female refers to sex = 'F'; 
RETRIEVED DEFINITIONS: ["patient who were born after 1930 refers to year(Birthday) > '1930'", "female refers to Sex = 'F'", "male patients refers to sex = 'M'", 'The larger the birthday value, the younger the person is, and vice versa', 'abnormal fibrinogen level refers to FG < = 150 or FG > = 450']
GOLD: SELECT CAST(SUM(CASE WHEN T2.PT >= 14 AND T1.SEX = 'F' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(CASE WHEN T2.PT >= 14 THEN 1 ELSE 0 END) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) > 55
PRED: SELECT CAST(SUM(CASE WHEN T1.SEX = 'F' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) 
FROM Patient AS T1 
INNER JOIN Laboratory AS T2 
ON T1.ID = T2.ID 
WHERE strftime('%Y', 'now') - strftime('%Y', T1.Birthday) > 55 AND (T2.PT <= 14 OR T2.PT >= 45)
ERROR: None

### 31. q994 (formula_1, challenging, conf 0.4)
Q: Which constructor scored most points from Monaco Grand Prix between 1980 and 2010? List the score, name and nationality of this team.
HINT (not shown to the agent): Monaco Grand Priz refers to the race; race in year between 1980 and 2010
RETRIEVED DEFINITIONS: ['Full name of the driver refers to drivers.forename and drivers.surname', 'constructor reference name refers to constructorRef', 'the time of the champion shows in the format of "minutes: seconds.millionsecond" in which Max(time)', 'website refers to url', 'the most points scored refers to max(points)']
GOLD: SELECT SUM(T1.points), T2.name, T2.nationality FROM constructorResults AS T1 INNER JOIN constructors AS T2 ON T1.constructorId = T2.constructorId INNER JOIN races AS T3 ON T3.raceid = T1.raceid WHERE T3.name = 'Monaco Grand Prix' AND T3.year BETWEEN 1980 AND 2010 GROUP BY T2.name ORDER BY SUM(T1.points) DESC LIMIT 1
PRED: SELECT SUM(T1.points) AS totalPoints, T3.constructorRef, T3.nationality 
FROM constructorResults AS T1 
INNER JOIN races AS T2 ON T1.raceId = T2.raceId 
INNER JOIN constructors AS T3 ON T1.constructorId = T3.constructorId 
WHERE T2.name = 'Monaco Grand Prix' AND T2.year BETWEEN 1980 AND 2010 
GROUP BY T1.constructorId 
ORDER BY totalPoints DESC 
LIMIT 1
ERROR: None

### 32. q186 (financial, moderate, conf 0.8)
Q: What percentage of male clients request for weekly statements to be issued?
HINT (not shown to the agent): Percentage of male clients = [count(male clients who requested weekly statements / count(clients who requested weekly statements)] * 100%; Male means gender = 'M'; 'POPLATEK TYDNE' stands for weekly issuance
RETRIEVED DEFINITIONS: ['Percentage of the male clients = DIVIDE(COUNT(male clients), COUNT(clients)) * 100', "Male refers to gender = 'M', A3 is the region name. A4 contains the information about inhabitants", "Male refers to gender = 'M'", 'k_symbol refers to the purpose of payments', 'Average salary can be found in A11']
GOLD: SELECT CAST(SUM(T1.gender = 'M') AS REAL) * 100 / COUNT(T1.client_id) FROM client AS T1 INNER JOIN district AS T3 ON T1.district_id = T3.district_id INNER JOIN account AS T2 ON T2.district_id = T3.district_id INNER JOIN disp as T4 on T1.client_id = T4.client_id AND T2.account_id = T4.account_id WHERE T2.frequency = 'POPLATEK TYDNE'
PRED: SELECT CAST(SUM(CASE WHEN T1.gender = 'M' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.client_id) 
FROM client AS T1 
INNER JOIN disp AS T2 ON T1.client_id = T2.client_id 
INNER JOIN account AS T3 ON T2.account_id = T3.account_id 
WHERE T3.frequency = 'POPLATEK TYDNE'
ERROR: None

### 33. q484 (card_games, moderate, conf 0.4)
Q: Please list the Italian names of the cards in the set Coldsnap with the highest converted mana cost.
HINT (not shown to the agent): card set Coldsnap refers to name = 'Coldsnap'; Italian refers to language = 'Italian'; highest converted mana cost refers to MAX(convertedManaCost)
RETRIEVED DEFINITIONS: ['converted mana cost higher than 5 refers to convertedManaCost > 5', "card set Coldsnap refers to name = 'Coldsnap'", "unknown power refers to power = '*' or T1.power is null", 'card costs more converted mana when the value of convertedManaCost is greater', 'with "Ancestor\'s Chosen" in the card set refers to name = \'Ancestor\'\'s Chosen\'']
GOLD: SELECT T2.name FROM foreign_data AS T1 INNER JOIN cards AS T2 ON T2.uuid = T1.uuid INNER JOIN sets AS T3 ON T3.code = T2.setCode WHERE T3.name = 'Coldsnap' AND T1.language = 'Italian' ORDER BY T2.convertedManaCost DESC
PRED: SELECT T3.translation 
FROM cards AS T1 
INNER JOIN sets AS T2 ON T2.code = T1.setCode 
INNER JOIN set_translations AS T3 ON T3.setCode = T2.code 
WHERE T2.name = 'Coldsnap' 
ORDER BY T1.convertedManaCost DESC 
LIMIT 1
ERROR: None

### 34. q94 (financial, challenging, conf 0.4)
Q: List out the account numbers of female clients who are oldest and has lowest average salary, calculate the gap between this lowest average salary with the highest average salary?
HINT (not shown to the agent): Female means gender = 'F'; A11 refers to average salary; Gap = highest average salary - lowest average salary; If the person A's birthdate > B's birthdate, it means that person B is order than person A.
RETRIEVED DEFINITIONS: ['A11 refers to average salary', "If the person A's birthdate < B's birthdate, it means that person B is younger than person A", 'Woman and female are closed', "Female refers to gender = 'F'", 'Average salary can be found in A11']
GOLD: SELECT T1.account_id , ( SELECT MAX(A11) - MIN(A11) FROM district ) FROM account AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id INNER JOIN disp AS T3 ON T1.account_id = T3.account_id INNER JOIN client AS T4 ON T3.client_id = T4.client_id WHERE T2.district_id = ( SELECT district_id FROM client WHERE gender = 'F' ORDER BY birth_date ASC LIMIT 1 ) ORDER BY T2.A11 DESC LIMIT 1
PRED: SELECT 
    T1.account_id,
    (SELECT MAX(A11) FROM district) - MIN(T4.A11) AS salary_gap
FROM 
    account AS T1
INNER JOIN 
    disp AS T2 ON T1.account_id = T2.account_id
INNER JOIN 
    client AS T3 ON T2.client_id = T3.client_id
INNER JOIN 
    district AS T4 ON T4.district_id = T1.district_id
WHERE 
    T3.gender = 'F'
ORDER BY 
    T3.birth_date ASC, T4.A11 ASC
LIMIT 1
ERROR: None

### 35. q1149 (thrombosis_prediction, moderate, conf 0.6)
Q: Are there more in-patient or outpatient who were male? What is the deviation in percentage?
HINT (not shown to the agent): male refers to SEX = 'M'; in-patient refers to Admission = '+'; outpatient refers to Admission = '-'; percentage = DIVIDE(COUNT(ID) where SEX = 'M' and Admission = '+', COUNT(ID) where SEX  = 'M' and Admission = '-')
RETRIEVED DEFINITIONS: ["female refers to Sex = 'F'", "patient who were born after 1930 refers to year(Birthday) > '1930'", "calculation = DIVIDE(COUNT(ID) where year(Birthday) > '1930' and SEX = 'F'), (COUNT(ID) where SEX = 'F')", "male patient refers to sex = 'M'", "followed up at the outpatient clinic refers to Admission = '-'"]
GOLD: SELECT CAST(SUM(CASE WHEN Admission = '+' THEN 1 ELSE 0 END) AS REAL) * 100 / SUM(CASE WHEN Admission = '-' THEN 1 ELSE 0 END) FROM Patient WHERE SEX = 'M'
PRED: SELECT 
    (CAST(SUM(CASE WHEN Admission = '+' THEN 1 ELSE 0 END) AS REAL) - 
     SUM(CASE WHEN Admission = '-' THEN 1 ELSE 0 END)) / 
    (SUM(CASE WHEN Admission = '+' THEN 1 ELSE 0 END) + 
     SUM(CASE WHEN Admission = '-' THEN 1 ELSE 0 END)) * 100 AS Deviation_Percentage
FROM 
    Patient
WHERE 
    SEX = 'M'
ERROR: None

### 36. q77 (california_schools, moderate, conf 0.4)
Q: Which schools served a grade span of Kindergarten to 9th grade in the county of Los Angeles and what is its Percent (%) Eligible FRPM (Ages 5-17)?
HINT (not shown to the agent): Percent (%) Eligible FRPM (Ages 5-17) can be acquired by `FRPM Count (Ages 5-17)` / `Enrollment (Ages 5-17)` * 100
RETRIEVED DEFINITIONS: ['Kindergarten to 8th grade refers to K-8', 'K-12 means grades 1 through 12', 'percent of eligible free rate for K-12 = `Free Meal Count (K-12)` * 100 / `Enrollment (K-12)`', 'non-chartered schools refer to schools whose Charter = 0', 'Eligible free rates for students aged 5-17 = `Free Meal Count (Ages 5-17)` / `Enrollment (Ages 5-17)`']
GOLD: SELECT T2.School, T1.`FRPM Count (Ages 5-17)` * 100 / T1.`Enrollment (Ages 5-17)` FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.County = 'Los Angeles' AND T2.GSserved = 'K-9'
PRED: SELECT T2.School, T1.`Percent (%) Eligible FRPM (Ages 5-17)` 
FROM frpm AS T1 
INNER JOIN schools AS T2 
ON T1.CDSCode = T2.CDSCode 
WHERE T2.County = 'Los Angeles' AND T2.GSoffered = 'K-9'
ERROR: None

### 37. q1107 (european_football_2, moderate, conf 0.8)
Q: When was the first time did Kevin Constant have his highest crossing score? Give the date.
HINT (not shown to the agent): Kevin Constant refers to player_name = 'Kevin Constant'; highest crossing score refers to MAX(crossing)
RETRIEVED DEFINITIONS: ["on 2016/6/23 refers to date LIKE '2016-06-23%'", "from 2007/2/22 to 2016/4/21 refers to the first 10 characters of date BETWEEN '2007-02-22' and '2016-04-21'", "league that had the most matches in the 2008/2009 season refers to MAX(league_name WHERE season = '2008/2009')", "2016 season refers to season = '2015/2016'", "in year 2011 refers to strftime('%Y', date) = '2011'"]
GOLD: SELECT `date` FROM ( SELECT t2.crossing, t2.`date` FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_fifa_api_id = t2.player_fifa_api_id WHERE t1.player_name = 'Kevin Constant' ORDER BY t2.crossing DESC) ORDER BY date DESC LIMIT 1
PRED: SELECT t2.date 
FROM Player AS t1 
INNER JOIN Player_Attributes AS t2 
ON t1.player_api_id = t2.player_api_id 
WHERE t1.player_name = 'Kevin Constant' 
ORDER BY t2.crossing DESC 
LIMIT 1
ERROR: None

### 38. q533 (codebase_community, simple, conf 0.6)
Q: How many users last accessed the website after 2014/9/1?
HINT (not shown to the agent): last accessed after 2014/9/1 refers to LastAccessDate > '2014-09-01'
RETRIEVED DEFINITIONS: ["user no. 24 refers to UserId = OwnerUserId = '24'", 'Name the user refers to DisplayName', 'average age = Divide (Sum(Age), Count(UserId))', 'creating more than 10 post refers to Count (UserId) > 10', 'total views refer to ViewCount']
GOLD: SELECT COUNT(Id) FROM users WHERE date(LastAccessDate) > '2014-09-01'
PRED: SELECT COUNT(Id) FROM users WHERE LastAccessDate > '2014-09-01'
ERROR: None

### 39. q846 (formula_1, moderate, conf 0.6)
Q: Please list the reference names of the drivers who are eliminated in the first period in race number 20.
HINT (not shown to the agent): driver reference name refers to driverRef; first qualifying period refers to q1; drivers who are eliminated in the first qualifying period refers to 5 drivers with MAX(q1); race number refers to raceId;
RETRIEVED DEFINITIONS: ['Full name of the driver refers to drivers.forename and drivers.surname', 'Alex Yoong refers to the full name of the driver', 'race number refers to raceId', 'track number less than 10 refers to position < 20', 'drivers who finished the race refers to time has value']
GOLD: SELECT T2.driverRef FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 20 ORDER BY T1.q1 DESC LIMIT 5
PRED: SELECT T1.driverRef 
FROM drivers AS T1 
INNER JOIN qualifying AS T2 ON T1.driverId = T2.driverId 
WHERE T2.raceId = 20 AND (T2.q1 IS NULL OR T2.q2 IS NULL OR T2.q3 IS NULL)
ERROR: None

### 40. q951 (formula_1, simple, conf 0.2)
Q: How many Japanese constructors have 0 points in 2 races?
HINT (not shown to the agent): 2 races refers to COUNT(raceID) = 2; Japanese refers to constructors.nationality = 'Japanese';
RETRIEVED DEFINITIONS: ['race at 291 refers to raceID = 291', 'COUNT(raceID) > 0 reveals that this driver participated in races', "Japanese refers to nationality = 'Japanese'", 'drivers who finished the race refers to time has value', 'race completion refers to time is not null']
GOLD: SELECT COUNT(T1.raceId) FROM constructorStandings AS T1 INNER JOIN constructors AS T2 on T1.constructorId = T2.constructorId WHERE T1.points = 0 AND T2.nationality = 'Japanese' GROUP BY T1.constructorId HAVING COUNT(raceId) = 2
PRED: SELECT COUNT(DISTINCT T2.constructorId) 
FROM constructorStandings AS T1 
INNER JOIN constructors AS T2 ON T1.constructorId = T2.constructorId 
WHERE T2.nationality = 'Japanese' AND T1.points = 0 AND T1.raceId IN (
    SELECT raceId 
    FROM constructorStandings 
    WHERE constructorId = T2.constructorId 
    GROUP BY constructorId 
    HAVING COUNT(*) >= 2
)
ERROR: None

### 41. q1257 (thrombosis_prediction, challenging, conf 0.4)
Q: Among the patients whose creatinine level is abnormal, how many of them aren't 70 yet?
HINT (not shown to the agent): creatinine level is abnormal refers to CRE >= 1.5; aren't 70 yet refers to SUBTRACT((YEAR(CURDATE()), YEAR(Birthday))) < 70; 
RETRIEVED DEFINITIONS: ["normal anti-scl70 refers to SC170 IN('negative', '0')", "female refers to SEX = 'F'", 'does not have any symptom refers to symptoms IS NULL', 'Should consider DISTINCT in the final result', 'abnormal platelet level refers to PLT <= 100 or PLT >= 400']
GOLD: SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.CRE >= 1.5 AND STRFTIME('%Y', Date('now')) - STRFTIME('%Y', T1.Birthday) < 70
PRED: SELECT COUNT(DISTINCT T1.ID) 
FROM Patient AS T1 
INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID 
WHERE T2.CRE > 1.5 AND JULIANDAY('now') - JULIANDAY(T1.Birthday) / 365.25 < 70
ERROR: None

### 42. q584 (codebase_community, moderate, conf 0.4)
Q: Write all the comments left by users who edited the post titled 'Why square the difference instead of taking the absolute value in standard deviation?'
HINT (not shown to the agent): "Why square the difference instead of taking the absolute value in standard deviation?" is the Title of post;
RETRIEVED DEFINITIONS: ['"Examples for teaching: Correlation does not mean causation" is the Title of post', 'the latest comment refers to MAX(CreationDate)', 'user who last edited refers to LastEditorUserId', '"Understanding what Dassault iSight is doing?" is the Title of post', 'in posts with 1 comment refers to CommentCount = 1']
GOLD: SELECT T2.Comment FROM posts AS T1 INNER JOIN postHistory AS T2 ON T1.Id = T2.PostId WHERE T1.Title = 'Why square the difference instead of taking the absolute value in standard deviation?'
PRED: SELECT T2.Text 
FROM posts AS T1 
INNER JOIN comments AS T2 ON T1.Id = T2.PostId 
INNER JOIN postHistory AS T3 ON T1.Id = T3.PostId 
WHERE T1.Title = 'Why square the difference instead of taking the absolute value in standard deviation?' AND T3.Comment LIKE '%edited%'
ERROR: None

### 43. q728 (superhero, moderate, conf 0.6)
Q: Rank superheroes from Marvel Comics by their eye color popularity, starting with the most common color.
HINT (not shown to the agent): the superheroes from Marvel Comics refers to publisher_name = 'Marvel Comics'; most common color refers to COUNT(superhero.id) DESC;
RETRIEVED DEFINITIONS: ["no eye color refers to colour = 'No Colour'", 'name refers to superhero_name', "published by Marvel Comics refers to publisher_name = 'Marvel Comics'", 'height from 170 to 190 refers to height_cm BETWEEN 170 AND 190', "heroes published by Marvel Comics refers to publisher_name = 'Marvel Comics'"]
GOLD: SELECT colour.colour AS EyeColor, COUNT(superhero.id) AS Count, RANK() OVER (ORDER BY COUNT(superhero.id) DESC) AS PopularityRank FROM superhero INNER JOIN colour ON superhero.eye_colour_id = colour.id INNER JOIN publisher ON superhero.publisher_id = publisher.id WHERE publisher.publisher_name = 'Marvel Comics' GROUP BY colour.colour
PRED: SELECT T2.colour, COUNT(*) AS EyeColorCount 
FROM superhero AS T1 
INNER JOIN colour AS T2 ON T1.eye_colour_id = T2.id 
INNER JOIN publisher AS T3 ON T1.publisher_id = T3.id 
WHERE T3.publisher_name = 'Marvel Comics' 
GROUP BY T2.colour 
ORDER BY EyeColorCount DESC
ERROR: None

### 44. q518 (card_games, moderate, conf 0.6)
Q: Which of the play format has the highest number of banned status? Indicate the play format and the names of all the card meet the condition.
HINT (not shown to the agent): play format refers to format; banned status refers to status = 'Banned'; the highest number of banned status refers to MAX(COUNT(status = 'Banned'))
RETRIEVED DEFINITIONS: ["legal for commander play format refers to format = 'commander' where status = 'Legal'", "commander play format refers to format = 'commander'", "banned cards refers to status = 'Banned'", "percentage refers to DIVIDE(COUNT(hasContentWarning = 0),COUNT(ID))*100 where format = 'commander' AND Status = 'legal'", "card set Coldsnap refers to name = 'Coldsnap'"]
GOLD: WITH MaxBanned AS (SELECT format, COUNT(*) AS count_banned FROM legalities WHERE status = 'Banned' GROUP BY format ORDER BY COUNT(*) DESC LIMIT 1) SELECT T2.format, T1.name FROM cards AS T1 INNER JOIN legalities AS T2 ON T2.uuid = T1.uuid INNER JOIN MaxBanned MB ON MB.format = T2.format WHERE T2.status = 'Banned'
PRED: SELECT T2.format, T1.name 
FROM cards AS T1 
INNER JOIN legalities AS T2 
ON T1.uuid = T2.uuid 
WHERE T2.status = 'Banned' 
GROUP BY T2.format 
ORDER BY COUNT(*) DESC 
LIMIT 1
ERROR: None

### 45. q1003 (formula_1, moderate, conf 0.4)
Q: How many accidents did the driver who had the highest number accidents in the Canadian Grand Prix have?
HINT (not shown to the agent): number of accidents refers to the number where statusid = 3; Canadian Grand Prix refers to the race of name

RETRIEVED DEFINITIONS: ['Only the time of the champion shows in the format of "hour: minutes: seconds.millionsecond"', "Chinese Grand Prix refers to races.name = 'Chinese Grand Prix'", 'Lewis Hamilton refers to the full name of the driver', 'Alex Yoong refers to the full name of the driver', 'finish time refers to time']
GOLD: SELECT COUNT(T1.driverId) FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN status AS T3 on T1.statusId = T3.statusId WHERE T3.statusId = 3 AND T2.name = 'Canadian Grand Prix' GROUP BY T1.driverId ORDER BY COUNT(T1.driverId) DESC LIMIT 1
PRED: SELECT COUNT(*) 
FROM results AS T1 
INNER JOIN status AS T2 ON T1.statusId = T2.statusId 
WHERE T2.status = 'Accident' AND T1.raceId IN (
    SELECT raceId 
    FROM races 
    WHERE name = 'Canadian Grand Prix'
)
ERROR: None

### 46. q1031 (european_football_2, challenging, conf 0.6)
Q: At present, calculate for the player's age who have a sprint speed of no less than 97 between 2013 to 2015.
HINT (not shown to the agent): players age at present = SUBTRACT((DATETIME(), birthday)); sprint speed of no less than 97 refers to sprint_speed > = 97; between 2013 to 2015 refers to YEAR(date) > = '2013' AND YEAR(date) < = '2015'; 
RETRIEVED DEFINITIONS: ["on 2016/6/23 refers to date LIKE '2016-06-23%'", '77 points overall rating refers to overall_rating = 77', 'The larger the birthday value, the younger the person is, and vice versa', 'percentage refers to DIVIDE(COUNT(height < 180 AND overall_rating > 70),COUNT(id)) * 100', "Landon Donovan's refers to player_name = 'Landon Donovan'; Jordan Bowery refers to player_name = 'Jordan Bowery'; percentage refers to DIVIDE(SUBTRACT(player_name = 'Landon Donovan' overall_rating; player_name = 'Jordan Bowery' overall_rating), player_name = 'Landon Donovan' overall_rating)*100"]
GOLD: SELECT DISTINCT DATETIME() - T2.birthday age FROM Player_Attributes AS t1 INNER JOIN Player AS t2 ON t1.player_api_id = t2.player_api_id WHERE STRFTIME('%Y',t1.`date`) >= '2013' AND STRFTIME('%Y',t1.`date`) <= '2015' AND t1.sprint_speed >= 97
PRED: SELECT 2023 - strftime('%Y', t1.birthday) AS age
FROM Player AS t1
INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id
WHERE t2.sprint_speed >= 97 AND t2.date BETWEEN '2013-01-01' AND '2015-12-31'
ERROR: None

### 47. q255 (toxicology, moderate, conf 0.6)
Q: What proportion of single bonds are carcinogenic? Please provide your answer as a percentage with five decimal places.
HINT (not shown to the agent): single bond refers to bond_type = '-'; label = '+' mean molecules are carcinogenic; proportion = DIVIDE(SUM(label = '+') * 100, COUNT(bond_id)) where bond_type = '-'
RETRIEVED DEFINITIONS: ["double bond refers to bond_type = '='", "label = '+' mean molecules are carcinogenic", "percentage = DIVIDE(SUM(bond_type = '#') * 100, COUNT(bond_id)) as percent where label = '+'", "percentage = DIVIDE(SUM(label = '+'), COUNT(molecule_id)) as percent", "percentage = DIVIDE(SUM(bond_type = '='), COUNT(bond_id)) as percent where molecule_id = 'TR008'"]
GOLD: SELECT ROUND(CAST(COUNT(CASE WHEN T2.label = '+' THEN T1.bond_id ELSE NULL END) AS REAL) * 100 / COUNT(T1.bond_id),5) FROM bond AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T1.bond_type = '-'
PRED: SELECT ROUND(CAST(COUNT(CASE WHEN T3.bond_type = '-' AND T2.label = '+' THEN T3.bond_id ELSE NULL END) AS REAL) * 100 / COUNT(T3.bond_id), 5) 
FROM atom AS T1 
INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id 
INNER JOIN bond AS T3 ON T2.molecule_id = T3.molecule_id
WHERE T3.bond_type = '-'
ERROR: None

### 48. q940 (formula_1, moderate, conf 0.8)
Q: Among the drivers that finished the race in the 2008 Chinese Grand Prix, how many of them have participated in Formula_1 races?
HINT (not shown to the agent): COUNT(raceID) > 0 reveals that this driver participated in races; drivers who finished the race refers to time has value.
RETRIEVED DEFINITIONS: ["Chinese Grand Prix refers to races.name = 'Chinese Grand Prix'", 'Lewis Hamilton refers to the full name of the driver', 'final rank refers to positionOrder', '2008 is the year of race', 'finish time refers to time']
GOLD: SELECT COUNT(*) FROM ( SELECT T1.driverId FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId WHERE T2.name = 'Chinese Grand Prix' AND T2.year = 2008 AND T1.time IS NOT NULL GROUP BY T1.driverId HAVING COUNT(T2.raceId) > 0 )
PRED: SELECT COUNT(DISTINCT driverId) FROM results WHERE raceId IN (SELECT raceId FROM races WHERE name = 'Chinese Grand Prix' AND YEAR = 2008)
ERROR: None

### 49. q1472 (debit_card_specializing, moderate, conf 0.6)
Q: In 2012, who had the least consumption in LAM?
HINT (not shown to the agent): Year 2012 can be presented as Between 201201 And 201212; The first 4 strings of the Date values in the yearmonth table can represent year.
RETRIEVED DEFINITIONS: ["Difference in annual average = SME's annual average - LAM's annual average", "Difference in annual average = LAM's annual average - KAM's annual average", 'annual average consumption of customer with the lowest consumption in each segment = total consumption per year / the number of customer with lowest consumption in each segment', 'Consumption decrease rate = (consumption_2012 - consumption_2013) / consumption_2012', 'Year 2013 can be presented as Between 201301 And 201312']
GOLD: SELECT T1.CustomerID FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Segment = 'LAM' AND SUBSTR(T2.Date, 1, 4) = '2012' GROUP BY T1.CustomerID ORDER BY SUM(T2.Consumption) ASC LIMIT 1
PRED: SELECT T1.CustomerID 
FROM customers AS T1 
INNER JOIN yearmonth AS T2 
ON T1.CustomerID = T2.CustomerID 
WHERE T1.Segment = 'LAM' AND T2.Date LIKE '2012%' 
ORDER BY T2.Consumption ASC 
LIMIT 1
ERROR: None
