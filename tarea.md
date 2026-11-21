# Database Diagrams

## ER Diagram

```mermaid


erDiagram
    direction TB

    Facility ||..|{ Vehicle : "Manages (1:M)"
    Vehicle ||..|{ Inspection : "Undergoes (1:M)"
    Technician ||..|{ Inspection : "Performs (1:M)"
    Inspection ||..|{ InspectionIssue : "HasIssue (1:M)"
    Vehicle ||..|{ WorkOrder : "HasOrder (1:M)"
    WorkOrder |o..|{ InspectionIssue : "Addresses (1:M)"
    WorkOrder ||..|{ CompletionEvent : "HasCompletion (1:M)"
    Technician }|..|{ WorkOrder : "AssignedTo (M:N)"
    WorkOrder }|..|{ ReplacementPart : "UsesPart (M:N)"
    WorkOrder ||..|{ StatusHistory : "HasStatusHistory (1:M)"
    Technician |o..|{ StatusHistory : "UpdatesStatus (1:M)"

    Facility {
        SERIAL facility_id PK
        VARCHAR(100) name
        VARCHAR(200) location
    }

    Vehicle {
        VARCHAR(17) vin PK
        VARCHAR(15) license_plate UK
        VARCHAR(50) manufacturer
        VARCHAR(50) model
        INTEGER manufacturing_year
        INTEGER current_mileage
    }

    Technician {
        SERIAL employee_id PK
        VARCHAR(100) name
        VARCHAR(100) specialization
    }

    Inspection {
        SERIAL inspection_id PK
        TIMESTAMP inspection_date
        INTEGER mileage
        VARCHAR(50) result
    }

    InspectionIssue {
        SERIAL issue_id PK
        TEXT description
        VARCHAR(20) severity
    }

    WorkOrder {
        SERIAL work_order_id PK
        TIMESTAMP creation_date
        VARCHAR(20) priority
        VARCHAR(20) current_status
        TEXT description
    }

    ReplacementPart {
        VARCHAR(50) part_number PK
        VARCHAR(100) name
        TEXT description
        NUMERIC current_catalog_price
    }

    CompletionEvent {
        SERIAL completion_id PK
        TIMESTAMP completed_at
        TEXT repair_summary
    }

    StatusHistory {
        SERIAL history_id PK
        INTEGER sequence_no
        VARCHAR(20) status_reached
        TIMESTAMP changed_at
    }
  ```
## Table Diagram
```mermaid
    
    erDiagram
    direction TB

    Facility ||..|{ Vehicle : "Manages (1:M)"
    Vehicle ||..|{ Inspection : "Undergoes (1:M)"
    Technician ||..|{ Inspection : "Performs (1:M)"
    Inspection ||..|{ InspectionIssue : "HasIssue (1:M)"
    Vehicle ||..|{ WorkOrder : "HasOrder (1:M)"
    WorkOrder |o..|{ InspectionIssue : "Addresses (1:M)"
    WorkOrder ||..|{ CompletionEvent : "HasCompletion (1:M)"
    WorkOrder ||--|{ WorkOrderAssignment : "has_assignments (1:M)"
    Technician ||--|{ WorkOrderAssignment : "receives_assignments (1:M)"
    WorkOrder ||--|{ WorkOrderPart : "uses (1:M)"
    ReplacementPart ||--|{ WorkOrderPart : "appears_in (1:M)"
    WorkOrder ||..|{ StatusHistory : "HasStatusHistory (1:M)"
    Technician |o..|{ StatusHistory : "UpdatesStatus (1:M)"

    Facility {
        SERIAL facility_id PK
        VARCHAR(100) name "NOT NULL"
        VARCHAR(200) location "NOT NULL"
    }

    Vehicle {
        VARCHAR(17) vin PK
        VARCHAR(15) license_plate UK "NOT NULL"
        VARCHAR(50) manufacturer "NOT NULL"
        VARCHAR(50) model "NOT NULL"
        INTEGER manufacturing_year "NOT NULL"
        INTEGER current_mileage "NOT NULL"
        INTEGER facility_id FK "NOT NULL"
    }

    Technician {
        SERIAL employee_id PK
        VARCHAR(100) name "NOT NULL"
        VARCHAR(100) specialization "NOT NULL"
    }

    Inspection {
        SERIAL inspection_id PK
        VARCHAR(17) vin FK "NOT NULL"
        INTEGER employee_id FK "NOT NULL"
        TIMESTAMP inspection_date "NOT NULL"
        INTEGER mileage "NOT NULL"
        VARCHAR(50) result "NOT NULL"
    }

    InspectionIssue {
        SERIAL issue_id PK
        INTEGER inspection_id FK "NOT NULL"
        TEXT description "NOT NULL"
        VARCHAR(20) severity "NOT NULL"
        INTEGER work_order_id FK "NULL allowed"
    }

    WorkOrder {
        SERIAL work_order_id PK
        VARCHAR(17) vin FK "NOT NULL; length normalized to Vehicle.vin"
        TIMESTAMP creation_date "NOT NULL"
        VARCHAR(20) priority "NOT NULL"
        VARCHAR(20) current_status "NOT NULL"
        TEXT description "NOT NULL"
    }

    ReplacementPart {
        VARCHAR(50) part_number PK
        VARCHAR(100) name "NOT NULL"
        TEXT description "NOT NULL"
        NUMERIC current_catalog_price "NUMERIC(10,2); NOT NULL"
    }

    WorkOrderAssignment {
        INTEGER work_order_id PK, FK "NOT NULL"
        INTEGER employee_id PK, FK "NOT NULL"
        TIMESTAMP assignment_date PK "NOT NULL"
        VARCHAR(50) assigned_role "NOT NULL"
        NUMERIC hours_worked "NUMERIC(6,2); NOT NULL"
        TIMESTAMP end_date "NULL allowed"
    }

    WorkOrderPart {
        INTEGER work_order_id PK, FK "NOT NULL"
        VARCHAR(50) part_number PK, FK "NOT NULL"
        INTEGER quantity "NOT NULL"
        NUMERIC unit_price_at_use "NUMERIC(10,2); NOT NULL"
    }

    CompletionEvent {
        SERIAL completion_id PK
        INTEGER work_order_id FK "NOT NULL"
        TIMESTAMP completed_at "NOT NULL"
        TEXT repair_summary "NOT NULL"
    }

    StatusHistory {
        SERIAL history_id PK
        INTEGER work_order_id FK "NOT NULL"
        INTEGER sequence_no "NOT NULL"
        VARCHAR(20) status_reached "NOT NULL"
        TIMESTAMP changed_at "NOT NULL"
        INTEGER employee_id FK "NULL allowed"
    }


    
```