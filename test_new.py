import json
import os
from llm_based_analysis import llm_resume_analysis
from App import pdf_reader  # Import the pdf_reader function from your app

def test_accuracy(test_json_path):
    # Load test data
    with open(test_json_path, 'r') as f:
        test_cases = json.load(f)
    
    total_cases = len(test_cases)
    field_weights = {
        "name": 0.2,
        "email": 0.2,
        "predicted_field": 0.2,
        "extracted_skills": 0.2,
        "user_level": 0.2
    }
    
    total_score = 0
    detailed_results = []
    
    for case in test_cases:
        pdf_path = case["path"]
        expected = case["output"]
        
        # Skip if PDF doesn't exist
        if not os.path.exists(pdf_path):
            print(f"File not found: {pdf_path}")
            continue
            
        # Process the PDF
        resume_text = pdf_reader(pdf_path)
        llm_response = llm_resume_analysis(resume_text)
        
        try:
            # Clean and parse the LLM response
            if "JSON Response:" in llm_response:
                llm_response = llm_response.replace("JSON Response:", "").strip()
            actual = json.loads(llm_response)
            
            # Calculate score for this test case
            case_score = 0
            case_results = {
                "pdf": pdf_path,
                "fields": {}
            }
            
            # Compare each field
            for field, weight in field_weights.items():
                if field in expected and field in actual:
                    if field == "extracted_skills":
                        # Special handling for skills - partial match
                        expected_skills = set(s.lower() for s in expected[field])
                        actual_skills = set(s.lower() for s in actual[field])
                        intersection = expected_skills.intersection(actual_skills)
                        union = expected_skills.union(actual_skills)
                        
                        if len(union) > 0:
                            similarity = len(intersection) / len(union)
                        else:
                            similarity = 0
                            
                        case_score += similarity * weight
                        case_results["fields"][field] = {
                            "expected": list(expected_skills),
                            "actual": list(actual_skills),
                            "match": similarity,
                            "weighted_score": similarity * weight
                        }
                    else:
                        # Exact match for other fields
                        if str(expected[field]).lower().replace(" ", "") == str(actual[field]).lower().replace(" ", ""):
                            similarity = 1
                        else:
                            similarity = 0
                            
                        case_score += similarity * weight
                        case_results["fields"][field] = {
                            "expected": expected[field],
                            "actual": actual[field],
                            "match": similarity,
                            "weighted_score": similarity * weight
                        }
            
            total_score += case_score
            case_results["case_score"] = case_score
            detailed_results.append(case_results)
            
        except json.JSONDecodeError as e:
            print(f"Error parsing LLM response for {pdf_path}: {e}")
            continue
    
    # Calculate overall accuracy
    if total_cases > 0:
        overall_accuracy = (total_score / total_cases) * 100
    else:
        overall_accuracy = 0
    
    return {
        "overall_accuracy": overall_accuracy,
        "total_test_cases": total_cases,
        "detailed_results": detailed_results
    }

def print_results(results):
    print(f"\n{'='*50}")
    print(f"Overall Accuracy: {results['overall_accuracy']:.2f}%")
    print(f"Test Cases Processed: {results['total_test_cases']}")
    print(f"{'='*50}\n")
    
    for case in results["detailed_results"]:
        print(f"PDF: {case['pdf']}")
        print(f"Case Score: {case['case_score']:.2f}")
        
        for field, details in case["fields"].items():
            print(f"\nField: {field}")
            print(f"Expected: {details['expected']}")
            print(f"Actual: {details['actual']}")
            print(f"Match: {details['match']:.2f}")
            print(f"Weighted Score: {details['weighted_score']:.2f}")
        
        print(f"\n{'-'*50}")

if __name__ == "__main__":
    # Path to your test.json file
    test_json_path = "test.json"
    
    # Run the tests
    results = test_accuracy(test_json_path)
    
    # Print the results
    print_results(results)
    
    # Save detailed results to a file
    with open("test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print("\nDetailed results saved to test_results.json")