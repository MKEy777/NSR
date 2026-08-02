# Response Letter — Group 1: Evaluation Protocols, Data Splitting, Statistics, and Main Results

## Overview of the revision

We thank the reviewers for identifying that the original manuscript did not distinguish the evaluation objectives, split units, and checkpoint-selection procedure with sufficient precision. In the revised manuscript, we retain the subject-dependent benchmark in Main Table 1 for like-for-like model comparison and add a separate subject-independent evaluation in the Supplementary Information to assess unseen-subject generalization. We have also added a dataset-wise protocol table and centralized descriptions of window construction, metadata, LDS scope, model selection, metric definitions, and statistical aggregation. The performance claims have been recalibrated to the evidence directly supported by each protocol.

The principal changes are as follows:

- **Main manuscript:** Main Table 1 is now explicitly identified as a **subject-dependent random window-level 80/20 evaluation**. The table note defines accuracy, macro-F1, and macro-specificity, states the split unit, and identifies which entries are reported as mean ± sample standard deviation. The Results text now limits the main claim to DA-SNN's consistently highest accuracy across the five subject-dependent benchmarks and directs readers to the subject-independent results in the Supplementary Information.
- **Supplementary Methods:** We added dataset-wise descriptions of subject/session/trial composition; non-overlapping outer-window construction; PSE temporal-bin lengths; subject/session/trial metadata; trial-wise LDS scope and ordering; subject-dependent and subject-independent split definitions; checkpoint selection; and metric/statistical aggregation.
- **Supplementary Results:** We added subject-independent comparisons using leave-one-subject-out (LOSO) evaluation for SEED, SEED-IV, and SEED-V, and five fixed subject-holdout splits for DEAP and DREAMER. These results are reported separately because they answer a different question from the subject-dependent main benchmark.

---

## Reviewer 1, Comment 1

> Although results are reported on five datasets, it is not clear how the experiments are actually conducted. For instance, the 96.98% accuracy on SEED is reported without specifying whether it is based on subject-dependent training or a cross-session setting. The same issue appears for DEAP and DREAMER, where the data splitting strategy is not described.

**Response:**

We agree that the original presentation did not identify the evaluation protocol with sufficient precision. We have now explicitly defined the result in Main Table 1 as a **subject-dependent random window-level 80/20 evaluation**: approximately 80% of the pooled outer windows are assigned to training and 20% to a held-out evaluation partition using class-stratified random splitting. Because the split unit is the outer window, subjects and trials may occur in both partitions. We therefore do not describe this result as cross-session, cross-trial, or unseen-subject generalization.

To separately evaluate generalization to unseen subjects, we added subject-independent experiments to the Supplementary Information. SEED, SEED-IV, and SEED-V use LOSO evaluation, in which all sessions, trials, and windows of one subject are held out. DEAP and DREAMER use five predefined subject-holdout splits: 26 training and 6 held-out subjects for DEAP, and 19 training and 4 held-out subjects for DREAMER. We deliberately describe these as **five fixed subject-holdout splits**, rather than standard fivefold cross-validation, because the splits are predefined subject partitions rather than a mutually exclusive fivefold coverage of all subjects.

The revised Supplementary Methods also provide the dataset composition: SEED and SEED-IV contain 15 subjects recorded in three sessions; SEED-V contains 20 subjects recorded in three sessions; DEAP contains 32 subjects and is treated as a single-session dataset; and DREAMER contains 23 subjects and is treated as a single-session dataset.

**Locations of changes:** Main Table 1 and the associated Results paragraph; Supplementary Methods, “Dataset Description,” “EEG Data Preprocessing,” and “Evaluation Protocols, Model Selection, and Statistics”; Supplementary Tables S3–S5.

---

## Reviewer 1, Comment 5 — Metric definitions

> In Table 1, metrics such as Acc, F1, and Spe are reported, but their definitions are not clearly given in the main text.

**Response:**

Thank you for this suggestion. We have defined all three metrics in the Main Table 1 note and in the Supplementary Methods. Accuracy is the proportion of correctly classified held-out windows. Macro-F1 is the unweighted mean of the per-class F1 scores. Macro-specificity is calculated in a one-versus-rest manner as TN/(TN+FP) for each class and then averaged equally across classes. We also clarify that the unit of evaluation is the outer window.

For statistical aggregation, mean values are arithmetic means and reported standard deviations are sample standard deviations calculated with `ddof = 1`. DA-SNN values in Main Table 1 are reported as mean ± sample standard deviation across repeated runs. The SEED-family LOSO results are reported as mean ± sample standard deviation across held-out-subject splits. The available DEAP and DREAMER cross-subject records contain aggregate point estimates over the five predefined splits; we therefore report these transparently without imputing unavailable dispersion values.

**Locations of changes:** Main Table 1 note; Supplementary Methods, “Evaluation Protocols, Model Selection, and Statistics”; Supplementary Tables S4 and S5.

---

## Reviewer 2, Comment 2

> Affective EEG signals are highly subject-dependent. While the paper reports exceptionally high accuracies across datasets, it fails to explicitly state whether these results are derived from “within-subject” or “cross-subject” (leave-one-subject-out) cross-validation. Given the wearable context, the omission of clear cross-subject generalization results is a critical concern.

**Response:**

We agree that subject-dependent benchmarking and unseen-subject generalization must be distinguished. The revision therefore separates the two evaluation objectives rather than presenting them as interchangeable evidence.

Main Table 1 retains the subject-dependent random window-level 80/20 benchmark, which supports comparison of the 15 models under that evaluation setting. The Supplementary Information now reports subject-independent results using LOSO for the three SEED-family datasets and fixed subject-holdout splits for DEAP and DREAMER. Under the subject-independent comparisons, DA-SNN ranks first in accuracy, macro-F1, and macro-specificity across all five datasets among the ten models evaluated. We do not directly compare the absolute values between the main and supplementary tables because the split units, held-out entities, and aggregation procedures differ. Instead, the two evaluations are presented as complementary: the main benchmark measures performance under subject-overlapping data availability, whereas the supplementary evaluation tests transfer to unseen subjects.

We have correspondingly narrowed the main-text claim. The revised Results state that DA-SNN achieves the highest **accuracy** on all five subject-dependent benchmarks, while metric-wise leadership in macro-F1 and macro-specificity varies across datasets. This avoids implying uniform dominance beyond what Main Table 1 supports.

**Locations of changes:** Abstract; Main Table 1 and Results; Supplementary Methods, “Evaluation Protocols, Model Selection, and Statistics”; Supplementary Results, “Subject-Independent Generalization Across EEG Benchmarks,” and Supplementary Tables S4–S5.

---

## Reviewer 3, Comment 5

> Some important experimental settings, such as training epochs, optimization strategies, or hardware-related configurations, are only briefly mentioned or scattered across sections. Consolidating these details would improve reproducibility.

**Response:**

We agree and have consolidated the EEG evaluation settings in the Supplementary Methods. In addition to the existing training-configuration table, the revision adds a dataset-wise protocol table reporting subject, session, and trial composition; outer-window duration; PSE temporal-bin structure; main split definition; and subject-independent split definition. The accompanying text specifies the split unit, held-out unit, metadata keys, LDS scope, model-selection rule, metric definitions, and statistical aggregation.

For completeness, we now state explicitly that **no separate validation subset was defined in any of the reported EEG protocols**. For each predefined split, the held-out evaluation partition was also used for epoch-wise checkpoint selection based on accuracy, after which the selected checkpoint was used to calculate the reported metrics on the same partition. Neural models in the unified reevaluation followed the same split definitions and checkpoint-selection rule. This common procedure supports comparisons within a given protocol, but we do not describe the resulting partition as an independent or untouched test set. In the subject-independent evaluations, all data from the held-out subjects nevertheless remain excluded from training-set construction and gradient-based parameter updates, although the held-out partition is used for checkpoint selection as stated above.

**Locations of changes:** Main Table 1 note and Methods pointer; Supplementary Methods, “Training Configuration” and “Evaluation Protocols, Model Selection, and Statistics”; Supplementary Table S3.

---

## Reviewer 4, Comment 20

> The validation protocol is under-specified and may inflate accuracy. The paper reports high accuracy across SEED, SEED-IV, SEED-V, DEAP, and DREAMER, but it does not clearly state whether splits are subject-dependent, subject-independent, cross-session, cross-trial, or random window-level. This is critical because the preprocessing uses overlapping windows. If adjacent windows from the same trial enter both training and test sets, the reported performance may be inflated.

**Response:**

We thank the reviewer for raising this important methodological concern. We have revised the manuscript to specify both the window construction and the relationship between preprocessing and data splitting.

First, the outer windows used in the experiments are **non-overlapping**, rather than overlapping. The SEED-family datasets use 4-s outer windows with a 4-s stride, with each window represented by four contiguous 1-s PSE bins. DEAP uses 9-s outer windows with a 9-s stride and six contiguous 1.5-s PSE bins, whereas DREAMER uses 9-s outer windows with a 9-s stride and nine contiguous 1-s PSE bins. The previously under-specified 1-s and 1.5-s quantities refer to the PSE temporal bins within an outer window, not to the stride between outer windows.

Second, each outer window retains subject, session, and trial identifiers. After PSE extraction and spatial mapping, LDS smoothing is applied separately within each trial along the temporally ordered sequence of outer windows at each fixed frequency–spatial coordinate. LDS never crosses trial, session, or subject boundaries. We also now state the remaining coupling transparently: LDS is performed on the complete trial sequence before data splitting, and the subject-dependent main benchmark randomly splits windows. Thus, different windows from the same trial may enter the training and held-out evaluation partitions after having participated in the same trial-wise smoothing operation. We do not claim trial-level independence or a fully leakage-free subject-dependent evaluation, and we limit the interpretation of Main Table 1 to comparison under this benchmark protocol.

Third, the newly added subject-independent evaluations address the reviewer's generalization concern under stricter subject separation. The held-out subject's complete data are excluded from training-set construction and gradient-based parameter updates, and LDS does not cross subject or trial boundaries. We also disclose that, across all reported EEG protocols, the held-out evaluation indices are used for epoch-wise checkpoint selection because no separate validation subset is present. This may lead to optimistic model-selection bias, so we no longer characterize the reported partition as an untouched test set. At the same time, the same predefined splits and checkpoint-selection rule are used for the neural-model reevaluations, preserving consistency for within-protocol comparisons.

**Locations of changes:** Main Table 1 caption/note and Results; Supplementary Methods, “EEG Data Preprocessing” and “Evaluation Protocols, Model Selection, and Statistics”; Supplementary Tables S1, S3–S5.
