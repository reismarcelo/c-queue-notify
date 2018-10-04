# C-queue-notify package

An NSO package that monitors other NSO services and sends a notification (i.e. REST POST call) when the commit-queue 
items associated with the service have completed. 

The callback mechanism relies on a new feature in NSO 4.6.2 and 4.7 (ENG-18680), which adds a commit-queue container to
the service plan. Even though this feature relies on plan component's plan-data, it is sufficient to just include the
plan-data grouping to the service yang model. The service itself is not required to write plan states. This means that
this model can be used by template-only or template+python service packages.

The instructions below use the service sample package (c-queue-notify-test package). The monitored service only needs to
include the ncs:plan-data grouping. Any monitored service with following basic structure would work:

    import tailf-ncs { 
        prefix ncs; 
    }
    
    list my-monitored-service {
        key name;
        leaf name {
            type string;
        }
        
        uses ncs:service-data;
        ncs:servicepoint my-monitored-service-servicepoint;
        uses ncs:plan-data;  
        
        ...
    }
 

## Configuration

A service monitor instance have the following configuration attributes:

    services c-queue-notify monitor1
     service-path /ncs:services/cq-notify-test:c-queue-test1/vrf
     rest
      uri      http://127.0.0.1:8080/api/running/services/rest-test-server
      payload  "<completed xmlns=\"http://cisco.com/services/cqueuenotifytest\"><name>{{ notifier }}-{{ service }}</name></completed>"
      username admin
      password admin
     !
    !


- service-path: Xpath leading to the root of the service. This dictates the kicker monitor tag that gets setup. More
                precisely, kicker monitor is constructed as "{service-path}/plan/commit-queue"

- rest uri:   URI used for the REST call. The notification will be a POST request to this URI.
- rest payload: This is the POST request payload. This is processed by a Jinja2 template engine, where the following
variables can be used:
    - service: the service instance that triggered the notification
    - notifier: the c-queue-notify id which was triggered
- rest username and password: credentials used for the POST request.


## Example

Basic setup of the sample services:

    services c-queue-test1
     global-settings
      asn 1
     !
    !
    services c-queue-test2
     global-settings
      asn 2
     !
    !
    
Setup c-queue-notify monitors for the two services above:

    services c-queue-notify monitor1
     service-path /ncs:services/cq-notify-test:c-queue-test1/vrf
     rest
      uri      http://127.0.0.1:8080/api/running/services/rest-test-server
      payload  "<completed xmlns=\"http://cisco.com/services/cqueuenotifytest\"><name>{{ notifier }}-{{ service }}</name></completed>"
      username admin
      password admin
     !
    !
    services c-queue-notify monitor2
     service-path /ncs:services/cq-notify-test:c-queue-test2/vrf
     rest
      uri      http://127.0.0.1:8080/api/running/services/rest-test-server
      payload  "<completed xmlns=\"http://cisco.com/services/cqueuenotifytest\"><name>{{ notifier }}-{{ service }}</name></completed>"
      username admin
      password admin
     !
    !

Create an instance of c-queue-test1 using commit-queues:

    admin@ncs(config)# services c-queue-test1
    admin@ncs(config-c-queue-test1)# vrf cust1
    Value for 'id' (<0-65535>): 2
    admin@ncs(config-vrf-cust1)# device [ XR-0 XR-1 ]
    admin@ncs(config-vrf-cust1)# commit commit-queue sync
    commit-queue {
        id 1538627263992
        status completed
    }
    Commit complete.

The REST notification is configured to create an entry under "services rest-test-server". Once the commit-queue item
completes we should then see a new entry there: 

    admin@ncs# show running-config services rest-test-server
    services rest-test-server
     completed monitor1-cust1
     !
    !

We can repeat the test with the other sample service:

    admin@ncs(config)# services c-queue-test2
    admin@ncs(config-c-queue-test2)# vrf cust2
    Value for 'id' (<0-65535>): 2
    admin@ncs(config-vrf-cust2)# device [ XR-0 XR-1 ]
    admin@ncs(config-vrf-cust2)# commit commit-queue sync
    commit-queue {
        id 1538627404022
        status completed
    }
    Commit complete.
    
    admin@ncs# show running-config services rest-test-server
    services rest-test-server
     completed monitor1-cust1
     !
     completed monitor2-cust2
     !
    !
