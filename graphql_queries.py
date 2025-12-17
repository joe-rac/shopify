
# 12/27/2024. ORDER_DETAILS is union of all shopify order fields needed for all apps. source of this query is results from Sidekick prompts and GrphiQL app.

ORDER_DETAILS = """
        name
        id
        note
        createdAt
        discountCodes
        cancelledAt
 
        customAttributes {
          key
          value
        }
        
        billingAddress {
          firstName
          lastName
          address1
          address2
          city
          province
          country
          zip
          phone
        }
        
        refunds(first: 100) {
          id
          createdAt
          note
          totalRefundedSet {
            shopMoney {
              amount
            }
          }
          refundLineItems(first: 100) {
            edges {
              node {
                lineItem {
                  sku
                  name
                  title
                  quantity
                  currentQuantity
                  originalUnitPrice
                  discountedUnitPrice 
                }
                quantity
                restockType
                priceSet {
                  shopMoney {
                    amount
                  }
                }
                subtotalSet {
                  shopMoney {
                    amount
                  }
                }
              }
            }
          }
        }
        
        events(first: 200) {
          edges {
            node {
              id
              createdAt
              message
              attributeToUser
            }
          }
        }
        
        currentTotalDiscountsSet {
          shopMoney {
            amount
            currencyCode
          }
        }
        
        totalPriceSet {
          shopMoney {
            amount
            currencyCode
          }
        }
        customer {
          firstName
          lastName
          email
          addresses(first: 100) {
            address1
            address2
            city
            province
            country
            zip
            phone
            company
          }      
        }
        
        lineItems(first: 100) {
          edges {
            node {
              title
              id
              sku
              name
              quantity
              currentQuantity
              refundableQuantity
              discountedTotalSet {
                shopMoney {
                  amount
                }
              }
              originalUnitPriceSet {
                shopMoney {
                  amount
                }
              }
              originalTotalSet {
                shopMoney {
                  amount
                }
              }
              discountedUnitPriceSet {
                shopMoney {
                  amount
                }
              }
              discountAllocations {
                allocatedAmountSet {
                  shopMoney {
                    amount
                  }
                }
              }
              customAttributes {
                key
                value
              }
            }
          }
          pageInfo {
            hasNextPage
            endCursor
          }
        }
"""

ORDERS_BY_SKU_BETWEEN_DATES = """
{
  orders(first: LIMIT, after: "END_CURSOR_HERE", query: "(sku:SKU_PREFIX_HERE*) AND created_at:>=CREATED_AT_MIN AND created_at:<CREATED_AT_MAX") {
    edges {
      node {
        INSERT_ORDER_DETAILS_HERE
      }
    }  
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""

ORDER_BY_NAME = """
{
  orders(query: "name:#ORDER_NUM",first: 10, ) {
    edges {
      node {
        INSERT_ORDER_DETAILS_HERE
      }
    }  
  }
}
"""

ORDER_BY_ORDER_ID = """
{
  order(id: "gid://shopify/Order/INSERT_ORDER_ID_HERE") {INSERT_ORDER_DETAILS_HERE}
}
"""

EVENTS_BY_ORDER_ID = """
  order(id: "gid://shopify/Order/INSERT_ORDER_ID_HERE") {
    events(first: 200) {
      edges {
        node {
          id
          createdAt
          message
          type
          subjectId
          subjectType
          verb
          attributeToUser {
            firstName
            lastName
          }
        }
      }
    }
  }
"""

MUTATE_CUSTOM_ATTRIBUTES = """
       mutation orderUpdate($input: OrderInput!) {
         orderUpdate(input: $input) {
         order {
           id
           customAttributes {
             key
             value
           }
         }
         userErrors {
           field
           message
         }
      }
    }
"""

