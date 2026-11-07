# SQL Joins: Combining Data from Multiple Tables

**Learning objective:** Differentiate INNER JOIN, LEFT JOIN and FULL OUTER JOIN and choose the correct join to answer a given query.  
**Duration:** 45 minutes (self-study or instructor-led)  
**Audience:** Undergraduate students who know basic SELECT queries

### By the end of this lesson you will be able to:

- **O1** Differentiate INNER JOIN, LEFT JOIN, and FULL OUTER JOIN semantics and results.
- **O2** Select the appropriate join type to answer a specific query scenario.
- **O3** Explain how NULL values and join order affect results and performance.

### Lesson plan

| # | Section | Type | Minutes | Objectives |
|---|---|---|---|---|
| 1 | Why do some rows disappear? | hook | 3 | O1, O2 |
| 2 | INNER JOIN – matching rows only | concept | 7 | O1 |
| 3 | LEFT (OUTER) JOIN – keep everything from the left | concept | 7 | O1, O3 |
| 4 | FULL OUTER JOIN – keep everything from both sides | concept | 5 | O1, O3 |
| 5 | Three‑table join and join order | example | 6 | O2, O3 |
| 6 | Hands‑on: Choose the right join | activity | 9 | O1, O2, O3 |
| 7 | Quiz – pick the right join | knowledge check | 6 | O1, O2, O3 |
| 8 | Key takeaways & common pitfalls | summary | 2 | O1, O2, O3 |
| | **Total** | | **45** | |

## 1. Why do some rows disappear? (3 min)

You have two tables – **students** and **enrollments**. Running `SELECT * FROM students;` shows 120 rows, but `SELECT * FROM students JOIN enrollments ON students.id = enrollments.student_id;` returns only 95 rows. *What happened to the missing 25 students?* This puzzle introduces the idea that different joins keep or discard rows.

## 2. INNER JOIN – matching rows only (7 min)

An **INNER JOIN** returns rows where the join condition is true for both tables. The syntax is:
```sql
SELECT …
FROM table1
INNER JOIN table2 ON table1.col = table2.col;
```
PostgreSQL describes this as combining rows that satisfy the expression [1]. When several joins are chained they nest left‑to‑right, and parentheses can change the nesting [2]. For INNER JOINs the nesting doesn't change the result, but for OUTER JOINs it can.

**Analogy:** Think of two circles overlapping; only the intersecting area (matching rows) is kept.

| students.id | name | enrollments.course_id |
|-------------|------|-----------------------|
| 1           | Ana  | 101                   |
| 2           | Ben  | 102                   |
| …           | …    | …                     |

## 3. LEFT (OUTER) JOIN – keep everything from the left (7 min)

A **LEFT OUTER JOIN** returns all rows from the left table and matching rows from the right; non‑matching right rows become `NULL`. Oracle defines it as preserving unmatched rows from the first table [3].
```sql
SELECT s.id, s.name, e.course_id
FROM students s
LEFT JOIN enrollments e ON s.id = e.student_id;
```
Rows without enrollments appear with `NULL` in `e.course_id`.

**NULL handling:** `NULL` never equals another `NULL`, so a left join can produce `NULL` values that must be considered in later calculations [4].

## 4. FULL OUTER JOIN – keep everything from both sides (5 min)

A **FULL OUTER JOIN** returns the union of a left and a right outer join: all rows from both tables, with `NULL` filling gaps where no match exists. PostgreSQL supports this join type [1].
```sql
SELECT s.id, e.course_id
FROM students s
FULL OUTER JOIN enrollments e ON s.id = e.student_id;
```
The result contains:
* rows with both sides matched,
* rows only in `students` (right side `NULL`),
* rows only in `enrollments` (left side `NULL`).

## 5. Three‑table join and join order (6 min)

Suppose we also have a **courses** table.
```sql
SELECT s.name, c.title, e.grade
FROM students s
JOIN enrollments e ON s.id = e.student_id
JOIN courses c ON e.course_id = c.id;
```
Joins nest left‑to‑right, and parentheses can change the nesting [2]. With INNER JOINs the database's query planner is free to reorder them for speed, so you write joins for *correctness* and let the optimizer handle performance [5].

**What if we need all students and all courses, even if no enrollment exists?**
```sql
SELECT s.name, c.title, e.grade
FROM students s
FULL OUTER JOIN enrollments e ON s.id = e.student_id
FULL OUTER JOIN courses c ON e.course_id = c.id;
```

## 6. Hands‑on: Choose the right join (9 min)

1. **Setup** (2 min) – Run the provided script to create `students`, `enrollments`, and `courses` with sample data.
2. **Task 1** (3 min) – Write a query that lists every student and the courses they are enrolled in; include students with no enrollments. (Use LEFT JOIN.)
3. **Task 2** (3 min) – Write a query that shows every course and any students enrolled; include courses with no students. (Use RIGHT JOIN or FULL OUTER JOIN.)
4. **Task 3** (2 min) – Explain how `NULL` appears in your results and why.
**Expected outcome:** Two result sets matching the description, with `NULL` values where no match exists.

## 7. Quiz – pick the right join (6 min)

1. Which join returns only rows that have matching keys in *both* tables?
   - A) LEFT JOIN  B) INNER JOIN  C) FULL OUTER JOIN
2. You need a list of all employees and any department they belong to; some employees have no department. Which join?
   - A) INNER  B) LEFT  C) RIGHT
3. After a LEFT JOIN, a column from the right table shows `NULL`. What does this indicate?
   - A) The left table row had no match  B) The right table column is actually NULL  C) The join failed
4. Which statement about join order is true?
   - A) JOINs are always evaluated left‑to‑right regardless of parentheses.
   - B) Parentheses can change the logical order and affect performance.
   - C) The order never matters for result correctness.
5. Full outer join is NOT supported natively in MySQL. How can you emulate it?
   - A) Use UNION of LEFT and RIGHT joins  B) Use CROSS JOIN  C) It cannot be emulated.

**Answer key**
1. B – INNER JOIN returns only matching rows [1].
2. B – LEFT JOIN keeps all left‑side rows [3].
3. A – `NULL` means no matching right‑side row [4].
4. B – Parentheses control order and can influence optimizer choices [2][5].
5. A – UNION of LEFT and RIGHT joins replicates FULL OUTER behavior.

## 8. Key takeaways & common pitfalls (2 min)

- **INNER** = keep only matches.
- **LEFT** = keep all left rows; unmatched right columns become `NULL`.
- **FULL** = keep all rows from both sides; `NULL` fills gaps.
- **NULL** never matches another `NULL`; test for it explicitly.
- With OUTER JOINs, order and parentheses can change the result. Check which table must keep all its rows.
- **Pitfall:** after a LEFT JOIN, a condition on the right table in `WHERE` (e.g. `WHERE e.grade > 50`) discards the NULL rows and silently turns it into an INNER JOIN. Put that condition in the `ON` clause instead.
- Common mistake: assuming a LEFT JOIN will remove rows – it never does.

## Supplementary videos (optional, not counted in the 45 minutes)

- **[SQL JOINs | INNER vs LEFT vs RIGHT vs FULL OUTER | Clearly Explained | Beginners Start Here!](https://www.youtube.com/watch?v=K9Y8P3X45kE)** - Maven Analytics, 9:19. Clear visual comparison of INNER, LEFT, and FULL OUTER joins. *Watch: after section s4.*
- **[Inner Join, Left Join, Right Join and Full Outer Join in SQL Server | SQL Server Joins](https://www.youtube.com/watch?v=KTvYHEntvn8)** - Questpond, 8:11. Demonstrates practical scenarios for choosing joins. *Watch: after activity s6.*

## References

1. PostgreSQL: Documentation: 18: 2.6. Joins Between Tables. *postgresql.org*. https://www.postgresql.org/docs/current/tutorial-join.html
2. PostgreSQL: Documentation: 18: 7.2. Table Expressions. *postgresql.org*. https://www.postgresql.org/docs/current/queries-table-expressions.html
3. LEFT OUTER JOIN operation - Oracle. *docs.oracle.com*. https://docs.oracle.com/javadb/10.8.3.0/ref/rrefsqlj18922.html
4. Join (SQL) - Wikipedia. *wikipedia.org*. https://en.wikipedia.org/wiki/Join_(SQL)
5. Joins - docs.oracle.com. *docs.oracle.com*. https://docs.oracle.com/en/database/oracle/oracle-database/26/sqlrf/Joins.html

### Books (further reading)

- Learning PHP, MySQL & JavaScript - Robin Nixon (2009). https://openlibrary.org/works/OL9559525W

### Videos

- SQL JOINs | INNER vs LEFT vs RIGHT vs FULL OUTER | Clearly Explained | Beginners Start Here! - Maven Analytics (9:19). https://www.youtube.com/watch?v=K9Y8P3X45kE
- Inner Join, Left Join, Right Join and Full Outer Join in SQL Server | SQL Server Joins - Questpond (8:11). https://www.youtube.com/watch?v=KTvYHEntvn8
