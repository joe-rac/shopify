
import copy
# install with
# pip install autocorrect
# use pip3 on mac
from autocorrect import Speller
from difflib import SequenceMatcher
import re
from collections import Counter

# 2/12/2026. All functions in this file are used to build the NEAFVendor.orderNumToCompanyMap dict which is used to merge individual order nums under a given company.
#            NEAFVendor.buildOrderNumToCompanyMap(raw) calls buildOrderNumToCompanyMap(raw) defined in this file.
#            All the other functions in this file are called by buildOrderNumToCompanyMap(raw).

def appendToKeyToOrderNumListMap(keyToOrderNumListMap,key,order_num):
    orderNumList = keyToOrderNumListMap.get(key,[])
    if not orderNumList:
        keyToOrderNumListMap[key] = orderNumList
    if order_num not in orderNumList:
        orderNumList.append(order_num)

    keys_to_delete = []
    for k, order_list in keyToOrderNumListMap.items():
        if k == key:
            continue
        if order_num in order_list:
            order_list.remove(order_num)
            if not order_list:
                keys_to_delete.append(k)

    for k in keys_to_delete:
        del keyToOrderNumListMap[k]

    return

def populate2MapsForKeyAndOrderNum(keyToOrderNumListMap,orderNumToKey,key,order_num,bothAreLists=False):

    # populate key->order_num list and order_num->key or key listmaps with passed in key and order_num
    # bothAreLists defaults to False because a given orderNum tends to map to a single key in orderNumToKey however it can be a list just as keyToOrderNumListMap maps to list.
    # if so pass in bothAreLists to True.

    if not key:
        return

    appendToKeyToOrderNumListMap(keyToOrderNumListMap,key,order_num)

    if bothAreLists:
        keyList = orderNumToKey.get(order_num,[])
        if not keyList:
            orderNumToKey[order_num] = keyList
        if key not in keyList:
            keyList.append(key)
    else:
        previousKey = orderNumToKey.get(order_num)
        if previousKey:
            raise Exception('order_num:{0} already maps to previousKey:{1} but we want to map it to new key:{2}'.format(order_num,previousKey,key))
        orderNumToKey[order_num] = key

    return

def normalizeCompany(company):
    if not company:
        return company
    chineseChars = re.findall(r'[\u4e00-\u9fff]+', company)
    if chineseChars:
        # 2/2/2022 added this for order 9218. company_from_property was good and was 'ZWO CO LTD.'
        return ''

    # 2/11/2026. used this to clean up the 2 different variants of Bob's Knobs in orders 15175 and 15400.
    company = company.translate(str.maketrans({
        "\u2019": "'",  # ’
        "\u2018": "'",  # ‘
        "\u201C": '"',  # “
        "\u201D": '"',  # ”
        "\u00A0": " ",  # NBSP
    }))

    toks = company.strip().split()
    return ' '.join(toks)

def upgradeFromOtherIdentifierToCompany(itemsUsedForCompany,itemToOrderNumMap,orderNumToCompanyFromPropertyMap,orderNumToCompanyMap,companyToOrderNumMap):
    failed_items = []
    for item in itemsUsedForCompany:
        order_nums = itemToOrderNumMap.get(item)
        if not order_nums:
            print("Item of '{0}' does not have entry in itemToOrderNumMap. That's bad. Fix the program.".format(item))
            failed_items.append(item)
            continue
        companies = []
        order_nums_with_company = []
        for order_num in order_nums:
            company = orderNumToCompanyFromPropertyMap.get(order_num)
            if company:
                order_nums_with_company.append(order_num)
                companies.append(company)
        if not companies:
            msg = "Item '{0}' has order_nums {1}. They do not have entry in orderNumToCompanyFromPropertyMap. That's bad. Fix program."
            print(msg.format(item,order_nums))
            failed_items.append(item)
            continue
        if len(companies) > 1:
            msg = "Item '{0}' has order_nums {1} but orderNumToCompanyFromPropertyMap[{2}] is {3}. We need 1 value. Fix program."
            print(msg.format(item,order_nums,order_num,companies))
            failed_items.append(item)
            continue
        for order_num in order_nums:
            if orderNumToCompanyMap[order_num] != companies[0]:
                print("Upgrading orderNumToCompanyMap[{0}] of '{1}' to '{2}'".format(order_num,orderNumToCompanyMap[order_num],companies[0]))
                orderNumToCompanyMap[order_num] = companies[0]
                appendToKeyToOrderNumListMap(companyToOrderNumMap,companies[0],order_num)

    return failed_items

def improveMultiTokenCompanyWithSingleTokenCompany(orderNumToCompanyMap,companyToOrderNumMap):

    # 2/9/2025. this function can eliminate ambiguous company names in orderNumToCompanyMap and companyToOrderNumMap.
    #           example are orders #15317 and #15705 for NEAF 2025.
    better_orderNumToCompanyMap = {}
    better_companyToOrderNumsMap = {}
    for order_num,company in orderNumToCompanyMap.items():
        single_token_candidate = []
        toks = company.split('|')
        if len(toks) > 1:
            # 2/9/2025. we have found a flawed multi-token company name of 'Amateur Astronomers Assoc. of Pittsburgh | Amateur Astronomers Assoc. of Pitt.' for order #15317.
            for tok in toks:
                tok = normalizeCompany(tok)
                for order_num_2,company_2 in orderNumToCompanyMap.items():
                    company_2 = normalizeCompany(company_2)
                    if company_2 == tok:
                        # 2/10/2026. we have found better single token company name of 'Amateur Astronomers Assoc. of Pittsburgh' for order #15705.
                        single_token_candidate.append(tok)
                        better_order_nums = better_companyToOrderNumsMap.get(tok,[])
                        if not better_order_nums:
                            better_companyToOrderNumsMap[tok] = better_order_nums
                            better_order_nums.append(order_num_2)
            if single_token_candidate:
                better_orderNumToCompanyMap[order_num] = Counter(single_token_candidate).most_common()[0][0]

    # 2/10/2026. rebuild orderNumToCompanyMap with single token upgrades.
    for order_num,company in better_orderNumToCompanyMap.items():
        old_company = orderNumToCompanyMap[order_num]
        better_order_nums = '|'.join([str(c) for c in better_companyToOrderNumsMap[company]])
        print(f"For order_num:{order_num} replace multi-token company:'{old_company}' with '{company}' from orders {better_order_nums}.")
        orderNumToCompanyMap[order_num] = company

        # 2/11/2026. adjust companyToOrderNumMap to match the rebuilt orderNumToCompanyMap.
        appendToKeyToOrderNumListMap(companyToOrderNumMap,company,order_num)

    return

def improveCompanyWithMatchingNameAndEmail(orderNumToCompanyMap,companyToOrderNumMap,emailToOrderNumMap,nameToOrderNumMap):
    emailToDuplicateCompanyMap = buildItemToDuplicateCompanyMap(orderNumToCompanyMap,emailToOrderNumMap)
    nameToDuplicateCompanyMap = buildItemToDuplicateCompanyMap(orderNumToCompanyMap,nameToOrderNumMap)

    for email,companies_from_email in emailToDuplicateCompanyMap.items():
        email_orders = emailToOrderNumMap.get(email)
        for name,companies_from_name in nameToDuplicateCompanyMap.items():
            name_orders = nameToOrderNumMap.get(name)

            company_name_counter = Counter([orderNumToCompanyMap[o] for o in name_orders])
            top2 = company_name_counter.most_common(2)
            is_tie = len(top2) >= 2 and top2[0][1] == top2[1][1]
            best_company = '' if is_tie else company_name_counter.most_common()[0][0]

            if set(companies_from_email) == set(companies_from_name) and set(email_orders) == set(name_orders) and best_company:

                companies_from_name_str = ', '.join(["'"+c+"'" for c in companies_from_name])
                orders_str = ', '.join([str(o) for o in email_orders])
                msg = f"Use '{best_company}' from company names {companies_from_name_str} because email {email}, name {name} and these companies all come from same set of orders of {orders_str}."
                print(msg)

                # rebuild companyToOrderNumMap using best_company
                companies_to_remove = copy.deepcopy(companies_from_name)
                companies_to_remove.remove(best_company)
                for company_to_remove in companies_to_remove:
                    order_nums_to_move = companyToOrderNumMap[company_to_remove]
                    del companyToOrderNumMap[company_to_remove]
                    order_nums = companyToOrderNumMap[best_company]
                    for order_num_to_move in order_nums_to_move:
                        order_nums.append(order_num_to_move)

                # rebuild orderNumToCompanyMap using best_company
                for order_num in name_orders:
                    if orderNumToCompanyMap[order_num] != best_company:
                        orderNumToCompanyMap[order_num] = best_company

    return

def improveCompanyWithCompanyFromProperty(orderNumToCompanyMap,companyToOrderNumMap,orderNumToCompanyFromPropertyMap,orderNumToEmailMap):
    for order_num,company in orderNumToCompanyMap.items():
        company_from_property = orderNumToCompanyFromPropertyMap.get(order_num)
        if company == company_from_property or not company_from_property:
            continue
        print("For order_num:{0} replacing company: '{1}' with company_from_property: '{2}'.".format(order_num,company,company_from_property))

        orderNums = companyToOrderNumMap[company]
        if not orderNums:
            # its already been changed. process next item.
            continue

        emailToOrderNumMap = {}
        for o_n in orderNums:
            email = orderNumToEmailMap.get(o_n)
            o_n_list = emailToOrderNumMap.get(email,[])
            if not o_n_list:
                emailToOrderNumMap[email] = o_n_list
            o_n_list.append(o_n)
        email = orderNumToEmailMap.get(order_num)
        orderNums_to_change_company = emailToOrderNumMap.get(email)

        for orderNum_to_change_company in orderNums_to_change_company:
            orderNumToCompanyMap[orderNum_to_change_company] = company_from_property
            orderNum_previous = companyToOrderNumMap.get(company,[])
            if order_num in orderNum_previous:
                if len(orderNum_previous) > 1:
                    # 12/17/2023. example when we had this complex change of company name we printed:
                    #             Removing order_num:13417 from orders list:[13443, 13442, 13441, 13417] for company 'Celestron' because its moving to 'Sky-Watcher'.
                    print("Removing order_num:{0} from orders list:{1} for company '{2}' because its moving to '{3}'.".format(order_num,orderNum_previous,company,company_from_property))
                orderNum_previous.remove(order_num)
                if not orderNum_previous:
                    del companyToOrderNumMap[company]

            orderNum_new = companyToOrderNumMap.get(company_from_property,[])
            if not orderNum_new:
                companyToOrderNumMap[company_from_property] = orderNum_new
            orderNum_new.append(orderNum_to_change_company)

    return

def getMostToksCompany(companies):
    tokCnt = []
    for c in companies:
        c = '' if c is None else c
        tokCnt.append(len(c.split()))
    tokCnt = sorted(tokCnt, reverse=True)
    if tokCnt[0] > tokCnt[1]:
        # we have a company name of maximum tokens. use it
        for c in companies:
            c = '' if c is None else c
            if len(c.split()) == tokCnt[0]:
                return c
        raise Exception('bug in getMostToksCompany processing {0}'.format(companies))
    return ''

def getCompanyFromAttribute(companies, companyFromAttributeToOrderNumMap):
    companies_from_attributes = []
    error = False
    company = None
    comment = None
    companyFromAttributeDesc = ''
    for comp in companies:
        order_nums = companyFromAttributeToOrderNumMap.get(comp)
        if order_nums:
            companies_from_attributes.append(comp)
            delim = ', ' if companyFromAttributeDesc else ''
            companyFromAttributeDesc += '{0}{1}:{2}'.format(delim, comp, ','.join([str(o_n) for o_n in order_nums]))
    if not companies_from_attributes:
        pass
    elif len(companies_from_attributes) == 1:
        company = companies_from_attributes[0]
        order_nums = companyFromAttributeToOrderNumMap.get(company)
        order_num_str = 'order_num {0}'.format(order_nums[0]) if len(order_nums) == 1 else 'order_nums {0}'.format(','.join([str(o_n) for o_n in order_nums]))
        comment = "Use '{0}' from {1} because it is company name from order_note_attributes for {2}.".format(company, companies, order_num_str)
    else:
        comment = 'it is not possible to pick one of {0} as best company name using companies from order note attributes.\n'\
                  'We can only do that if a single one of these companies had been set as an order note attribute but these companies were set as order note attributes in these orders:\n{1}'
        comment = comment.format(companies,companyFromAttributeDesc)
        error = True
    return company, comment, error

def getOneMixedCaseCompany(companies):
    mixedCaseCompanies = []
    for company in companies:
        toks = company.split()
        for tok in toks:
            mixedCase = tok.upper() != tok and tok.lower() != tok
            if mixedCase:
                mixedCaseCompanies.append(company)
                break
    return mixedCaseCompanies[0] if len(mixedCaseCompanies) == 1 else ''

def getOneBestSpelledCompany(companies):
    spell = Speller(lang='en')
    companyToSpellingQualityCntMap = {}

    for company in companies:
        c = company.replace('-', ' ').replace(',', ' ').replace('.', ' ')
        toks = c.split()

        spellingQuality = 0.0
        numToks = len(toks)
        for tok in toks:
            tokSpelled = spell(tok)
            if tokSpelled == tok:
                spellingQuality += 1. / numToks
            else:
                closeness = SequenceMatcher(a=tokSpelled, b=tok).ratio()
                spellingQuality += closeness / numToks

        companyToSpellingQualityCntMap[company] = spellingQuality

    # pick company of highest spelling quality.
    bestSpellingQuality = 0.0
    bestCompany = None
    for company, spellingQuality in companyToSpellingQualityCntMap.items():
        if abs(spellingQuality - bestSpellingQuality) <= 0.0001:
            # we have more than 1 company with the same best spelling quality. give up in defaeat.
            return ''
        if spellingQuality > bestSpellingQuality:
            bestSpellingQuality = spellingQuality
            bestCompany = company

    return bestCompany

def getBestCompany(companies, companyFromAttributeToOrderNumMap):

    error = False
    company, comment, error = getCompanyFromAttribute(companies, companyFromAttributeToOrderNumMap)
    if error:
        return company, comment, error
    if company:
        return company, comment, error
    company = getMostToksCompany(companies)
    if company:
        comment = "Use '{0}' which is company name of most tokens in {1}".format(company, companies)
        return company, comment, error
    company = getOneMixedCaseCompany(companies)
    if company:
        comment = "Use '{0}' which is mixed case company name of companies:{1}".format(company, companies)
        return company, comment, error
    company = getOneBestSpelledCompany(companies)
    if company:
        comment = "Use '{0}' which is best spelled company name of companies:{1}".format(company, companies)
        return company, comment, error
    company = ' | '.join(companies)
    comment = "Failed to find best company of {0}. Give up and return concatenation of '{1}'.".format(companies,company)
    return company, comment, error

def buildItemToDuplicateCompanyMap(orderNumToCompanyMap,itemToOrderNumMap):
    itemToDuplicateCompanyMap = {}
    for item,orderNums in itemToOrderNumMap.items():
        if len(orderNums) == 1:
            continue
        companies = [orderNumToCompanyMap.get(order_num) for order_num in orderNums if orderNumToCompanyMap.get(order_num)]
        companies = set(companies)
        if len(companies) <= 1:
            continue
        itemToDuplicateCompanyMap[item] = list(companies)
    return itemToDuplicateCompanyMap

def findDuplicateIdentifiers(orderNumToCompanyMap,itemLabel,itemToOrderNumMap):
    itemToDuplicateCompanyMap = buildItemToDuplicateCompanyMap(orderNumToCompanyMap,itemToOrderNumMap)
    for item,companies in itemToDuplicateCompanyMap.items():
        orderNums = itemToOrderNumMap[item]
        msg = "The {0} {1} with orderNums {2} is associated with companies {3}. THAT'S ODD THAT THE SAME {0} IS ASSOCIATED WITH {4} COMPANIES."
        msg = msg.format(itemLabel,item,orderNums,companies,len(companies))
        print(msg)
    return

def companySanityCheck(orderNumToCompanyMap,emailToOrderNumMap,nameToOrderNumMap):
    # 2/7/2022. do sanity check of company names. nothing in this function is used for implementing this system.

    companies =  set(orderNumToCompanyMap.values())
    print('{0} distinct companies distributed over {1} distinct orders.'.format(len(companies),len(orderNumToCompanyMap)))
    print('{0} distinct emails, {1} distinct names'.format(len(emailToOrderNumMap),len(nameToOrderNumMap)))

    findDuplicateIdentifiers(orderNumToCompanyMap,'email',emailToOrderNumMap)
    findDuplicateIdentifiers(orderNumToCompanyMap,'name',nameToOrderNumMap)

    return

def improveCompanyFromPropertyWithOtherItem(itemLabel,companyFromPropertyToOrderNumMap,orderNumToCompanyFromPropertyMap,itemToOrderNumMap,companyFromAttributeToOrderNumMap):

    itemToDuplicateCompanyFromPropertyMap = {}
    for item, orderNums in itemToOrderNumMap.items():
        companies = []
        for order_num in orderNums:
            companiesFromProperty = orderNumToCompanyFromPropertyMap.get(order_num, [])
            companies.extend([companyFromProperty for companyFromProperty in companiesFromProperty if companyFromProperty])

        companies = set(companies)
        if len(companies) <= 1:
            continue
        itemToDuplicateCompanyFromPropertyMap[item] = list(companies)

    itemToDuplicateCompanyFromPropertyMap_improved = {}
    for item, companies in itemToDuplicateCompanyFromPropertyMap.items():
        company, comment, error = getBestCompany(companies, companyFromAttributeToOrderNumMap)
        if comment:
            comment = "Using {0} of '{1}' ".format(itemLabel,item) + comment
            print(comment)
        if not error:
            itemToDuplicateCompanyFromPropertyMap_improved[item] = company

    # 4/2/2023. we have improved itemToDuplicateCompanyFromPropertyMap using getBestCompany in above loop. those improved items are in itemToDuplicateCompanyFromPropertyMap_improved.
    # upgrade itemToDuplicateCompanyFromPropertyMap with those improved items:
    itemToDuplicateCompanyFromPropertyMap.update(itemToDuplicateCompanyFromPropertyMap_improved)

    first = True
    for item,companyFromProperty in itemToDuplicateCompanyFromPropertyMap.items():
        if isinstance(companyFromProperty,list):
            # 4/3/2023. we have failed to find a best company for this item. an example is itemLabel of 'name' with name of 'Emily Rice'. We arrive here with companyFromProperty
            # ['STARtorialist, Inc.', 'CUNY Astronomy']. This failure is expected because, oddly enough, Emily Rice is associated with these 2 completely different companies.
            continue
        orderNums = itemToOrderNumMap[item]
        companies = []
        for orderNum in orderNums:
            company_from_map = orderNumToCompanyFromPropertyMap.get(orderNum)
            if not company_from_map:
                # 3/22/2025. this block added for Dwarf Lab order 15601. its for Advertising $50 to $2000. No mandatory company in product(from App of "PC - Product Optiobns")
                #            so no entry in orderNumToCompanyFromPropertyMap. they have total of 3 orders: 15355, 15601, 15782
                continue
            companies.extend(company_from_map)
        # companies = set(companies)
        # msg = "{0} of {1} in orderNums {2} has best companyFromProperty of '{3}' that will replace these companyFromProperties of {4}"
        #print(msg.format(itemLabel,item,orderNums,companyFromProperty,companies))
        for orderNum in orderNums:
            old_companyFromProperties = orderNumToCompanyFromPropertyMap.get(orderNum)
            if not old_companyFromProperties:
                # 3/22/2025. this block added for Dwarf Lab order 15601. its for Advertising $50 to $2000. No mandatory company in product(from App of "PC - Product Optiobns")
                #            so no entry in orderNumToCompanyFromPropertyMap. they have total of 3 orders: 15355, 15601, 15782
                continue
            if len(old_companyFromProperties)==1 and old_companyFromProperties[0] == companyFromProperty:
                # no need to make any improvement to companyFromProperty for orderNum. it already matches the improved value
                continue
            msg = "Using {0} of '{1}' to replace old value of orderNumToCompanyFromPropertyMap[{2}] of {3} with ['{4}']."
            print(msg.format(itemLabel,item,orderNum,old_companyFromProperties,companyFromProperty))
            orderNumToCompanyFromPropertyMap[orderNum] = [companyFromProperty]

    # invert orderNumToCompanyFromPropertyMap and re-populate companyFromPropertyToOrderNumMap

    companyFromPropertyToOrderNumMap.clear()
    for orderNum,companiesFromProperties in orderNumToCompanyFromPropertyMap.items():
        for companyFromProperty in companiesFromProperties:
            cfp_list = companyFromPropertyToOrderNumMap.get(companyFromProperty,[])
            if not cfp_list:
                companyFromPropertyToOrderNumMap[companyFromProperty] = cfp_list
            cfp_list.append(orderNum)

    return

def buildOrderNumToCompanyMap_for_extra_ss_rows(raw):

    # 3/16/2026. find all company names specified by orders using "Get booths from this order" property and return them in orderNumToCompanyMap_for_extra_ss_rows dict.

    orderNumToCompanyMap_for_extra_ss_rows = {}
    error = ''
    ex_prefix = "Error caught in buildOrderNumToCompanyMap_for_extra_ss_rows.\n"

    for order_num,nvt in raw.items():
        if not nvt.get_booths_from_order:
            continue
        order_num = int(order_num.strip())
        try:
            get_booths_from_order = int(nvt.get_booths_from_order)
        except ValueError:
            error = f"{ex_prefix}order_num:{order_num}, nvt.get_booths_from_order:'{nvt.get_booths_from_order}' is not valid. Must be string in int form."
            return orderNumToCompanyMap_for_extra_ss_rows,error
        if nvt.get_booths_from_order not in raw:
            error = f"{ex_prefix}order_num:{order_num}, nvt.get_booths_from_order:'{nvt.get_booths_from_order} is invalid. It is not in NEAFVendor.raw dict."
            return orderNumToCompanyMap_for_extra_ss_rows,error
        if order_num == get_booths_from_order:
            error = f"{ex_prefix}order_num:{order_num}, nvt.get_booths_from_order:'{nvt.get_booths_from_order} equals order_num. It must refer to other item in NEAFVendor.raw dict."
            return orderNumToCompanyMap_for_extra_ss_rows,error
        if not nvt.company_from_property:
            error = f"{ex_prefix}order_num:{order_num}, nvt.get_booths_from_order:'{nvt.get_booths_from_order} but nvt.company_from_property list is missing."
            return orderNumToCompanyMap_for_extra_ss_rows,error
        if len(nvt.company_from_property) != 1:
            error = f"{ex_prefix}order_num:{order_num}, nvt.get_booths_from_order:{nvt.get_booths_from_order} but nvt.company_from_property:{nvt.company_from_property} must have len of 1."
            return orderNumToCompanyMap_for_extra_ss_rows,error
        orderNumToCompanyMap_for_extra_ss_rows[order_num] = normalizeCompany(nvt.company_from_property[0])

    return orderNumToCompanyMap_for_extra_ss_rows,error

def buildOrderNumToCompanyMap(raw):

    # 2/12/2026. this is function called by NEAFVendor.orderNumToCompanyMap.

    # these are the 10 maps that are used to build the final result of self.orderNumToCompanyMap
    companyToOrderNumMap = {} # >1 orderNum. 'Andover Corporation', 'Celestron', 'Hutech Corporation', 'Rockland Astronomy Club', 'Software Bisque, Inc.', 'Spaceflux' and others
    emailToOrderNumMap = {} # >1 orderNum. 'Peter@Bisque.com', 'anita.maier@nimax.de', 'dixie.richards@andovercorp.com', 'kkawai@celestron.com', and others
    nameToOrderNumMap = {} # >1 orderNum. 'Anita Maier', 'Babak Sedehi', 'Dixie Richards', 'Kevin Kawai', 'Ludovic Nachury', 'Marco Rocchetto', 'Peter Hardy', 'Rori Baldari'
    companyFromPropertyToOrderNumMap = {}
    companyFromAttributeToOrderNumMap = {} # >1 orderNum.  'Unistellar', 'NexDome Observatories', 'Andover Corporation', 'Celestron', 'Software Bisque, Inc.', 'Unistellar', 'nimax GmbH'
    orderNumToCompanyMap = {}
    orderNumToEmailMap = {}
    orderNumToNameMap = {}
    orderNumToCompanyFromPropertyMap = {} # >1 item. 9114, 9143, 9258, 9281, 92849285
    orderNumToCompanyFromAttributeMap = {}

    # these collections used to keep track of troublesome order_num to company mappings.
    orderNumsMissingCompanies = []
    orderNumsMissingCompanies2 = []
    orderNumsMissingCompanies3 = []
    emailsUsedForCompany = []
    namesUsedForCompany = []

    orderNumToCompanyMap_for_extra_ss_rows,error = buildOrderNumToCompanyMap_for_extra_ss_rows(raw)
    if error:
        return orderNumToCompanyMap,error

    # populate the 9 maps with raw data. the 2 company maps and 2 companyFromProperty maps are adjusted later.
    i = 0
    debug = False
    error = ''
    for order_num,nvt in raw.items():
        order_num = int(order_num.strip())
        if order_num in orderNumToCompanyMap_for_extra_ss_rows:
            # 3/16/2026.
            continue
        company = normalizeCompany(nvt.company)
        company_from_attribute = normalizeCompany(nvt.company_from_attribute)
        populate2MapsForKeyAndOrderNum(companyFromAttributeToOrderNumMap,orderNumToCompanyFromAttributeMap,normalizeCompany(company_from_attribute),order_num)
        if not company:
            orderNumsMissingCompanies.append(order_num)
        company_from_property = nvt.company_from_property
        email = nvt.email
        name = nvt.name
        if debug:
            msg = 'i:{0}, order_num:{1}, company:{2}, company_from_property:{3}, company_from_attribute:{4}, email:{5}, name:{6}'
            print(msg.format(i,order_num,company,company_from_property,company_from_attribute,email,name))
        populate2MapsForKeyAndOrderNum(companyToOrderNumMap,orderNumToCompanyMap,company,order_num)
        populate2MapsForKeyAndOrderNum(emailToOrderNumMap,orderNumToEmailMap,email,order_num)
        populate2MapsForKeyAndOrderNum(nameToOrderNumMap,orderNumToNameMap,name,order_num)
        for cfp in company_from_property:
            populate2MapsForKeyAndOrderNum(companyFromPropertyToOrderNumMap,orderNumToCompanyFromPropertyMap,normalizeCompany(cfp),order_num,bothAreLists=True)
        i += 1

    print('9 basic maps populated.\nThe 4 items to scalar orderNum Maps have these sizes:')
    msg = 'companyToOrderNumMap:{0}  companyFromPropertyToOrderNumMap:{1}  emailToOrderNumMap:{2}  nameToOrderNumMap:{3}'
    print(msg.format(len(companyToOrderNumMap),len(companyFromPropertyToOrderNumMap),len(emailToOrderNumMap),len(nameToOrderNumMap)))
    print('The 5 orderNum to item lists have these sizes:')
    msg = 'orderNumToCompanyMap:{0}  orderNumToEmailMap:{1}  orderNumToNameMap:{2}  orderNumToCompanyFromPropertyMap:{3}  orderNumToCompanyFromAttributeMap:{4}'
    print(msg.format(len(orderNumToCompanyMap),len(orderNumToEmailMap),len(orderNumToNameMap),len(orderNumToCompanyFromPropertyMap),len(orderNumToCompanyFromAttributeMap)))

    improveCompanyFromPropertyWithOtherItem('email',companyFromPropertyToOrderNumMap,orderNumToCompanyFromPropertyMap,emailToOrderNumMap,companyFromAttributeToOrderNumMap)
    improveCompanyFromPropertyWithOtherItem('name',companyFromPropertyToOrderNumMap,orderNumToCompanyFromPropertyMap,nameToOrderNumMap,companyFromAttributeToOrderNumMap)

    # backfill in orderNumsMissingCompanies with company_from_property if possible. Failing that try backfilling with name, then email
    for order_num in orderNumsMissingCompanies:
        companies_from_property = orderNumToCompanyFromPropertyMap.get(order_num)
        name = orderNumToNameMap.get(order_num)
        email = orderNumToEmailMap.get(order_num)
        if companies_from_property:
            company = companies_from_property[0]
            if len(companies_from_property) > 1:
                print('Company is missing and more than one choice in companies_from_property:{0}. Pick one later.'.format(companies_from_property))
                orderNumsMissingCompanies2.append(order_num)
            else:
                orderNumToCompanyMap[order_num] = company
                appendToKeyToOrderNumListMap(companyToOrderNumMap,company,order_num)
        else:
            if name:
                print('Company is missing and companies_from_property is missing for order_num:{0}. use name:{1} from that order_num.'.format(order_num,name))
                namesUsedForCompany.append(name)
                company = name
            elif email:
                print('Company is missing and companies_from_property is missing and name is missing for order_num:{0}. use email:{1} from that order_num.'.format(order_num,email))
                emailsUsedForCompany.append(email)
                company = email
            else:
                raise Exception('both name and email missing for order_num:{0}'.format(order_num))
            orderNumToCompanyMap[order_num] = company
            appendToKeyToOrderNumListMap(companyToOrderNumMap,company,order_num)

    # improve orderNumToCompanyFromPropertyMap with getBestCompany.

    for order_num,companies in orderNumToCompanyFromPropertyMap.items():
        if len(companies) == 1:
            # no choice of best company name needed. there is only one
            orderNumToCompanyFromPropertyMap[order_num] = companies[0]
        else:
            company,comment,error = getBestCompany(companies,companyFromAttributeToOrderNumMap)
            if error:
                error += '\n' + comment if error else comment
            if comment:
                print(comment)
            # found best company name
            orderNumToCompanyFromPropertyMap[order_num] = company

    # supplement orderNumToCompanyMap with orderNumToCompanyFromPropertyMap
    for order_num in orderNumsMissingCompanies2:
        company = orderNumToCompanyFromPropertyMap.get(order_num)
        if company:
            orderNumToCompanyMap[order_num] = company
            appendToKeyToOrderNumListMap(companyToOrderNumMap,company,order_num)
        else:
            # orderNumsMissingCompanies3 is informational. for now, it's not used for anything.
            orderNumsMissingCompanies3.append(order_num)

    failed_names = upgradeFromOtherIdentifierToCompany(namesUsedForCompany,nameToOrderNumMap,orderNumToCompanyFromPropertyMap,orderNumToCompanyMap,companyToOrderNumMap)
    failed_emails = upgradeFromOtherIdentifierToCompany(emailsUsedForCompany,emailToOrderNumMap,orderNumToCompanyFromPropertyMap,orderNumToCompanyMap,companyToOrderNumMap)

    if failed_names:
        print("These names of {0} are being used for company. That's bad. Need a real company name. Fix program.".format(failed_names))
    if failed_emails:
        print("These emails of {0} are being used for company. That's bad. Need a real company name. Fix program.".format(failed_emails))

    improveCompanyWithCompanyFromProperty(orderNumToCompanyMap,companyToOrderNumMap,orderNumToCompanyFromPropertyMap,orderNumToEmailMap)
    improveMultiTokenCompanyWithSingleTokenCompany(orderNumToCompanyMap,companyToOrderNumMap)
    improveCompanyWithMatchingNameAndEmail(orderNumToCompanyMap,companyToOrderNumMap,emailToOrderNumMap,nameToOrderNumMap)

    # this is the final upgrade to company. if we have a user entered override name in company_from_attribute it takes priority over all other adjustments
    for order_num,company_from_attribute in orderNumToCompanyFromAttributeMap.items():
        company = orderNumToCompanyMap[order_num]
        print("For order_num:{0} replacing company: '{1}' with company_from_attribute: '{2}'".format(order_num,company,company_from_attribute))
        orderNumToCompanyMap[order_num] = company_from_attribute
        orderNums = companyToOrderNumMap.get(company)
        if not orderNums:
            # 1/30/2023. this happened when I was screwing around trying to enter order #11719 for Rowan Astronomy but using my email. It clobbered my address info and
            # all customer details under Joe Moskowitz picked up Rowan Astronomy details. I deleted #11719. Lesson is can't build fake order with my email.
            print("Major screw-up for order_num:{0}, company:'{1}'. companyToOrderNumMap['{1}'] has no entry. FIX THE PROGRAM.".format(order_num,company))
        else:

            # 3/16/2023. example is order_num 11607 and company_from_attribute 'Sky-Watcher' where companyToOrderNumMap['Celestron'] is [11617, 11607, 9368, 9132]
            # and should be changed to [11617, 9368, 9132] and companyToOrderNumMap['Sky-Watcher'] is missing and needs [11607]
            if order_num in orderNums:
                orderNums.remove(order_num)
            orderNums_new = companyToOrderNumMap.get(company_from_attribute,[])
            if not orderNums_new:
                companyToOrderNumMap[company_from_attribute] = orderNums_new
            orderNums_new.append(order_num)

            # 3/16/2023. same example as above where orderNumToCompanyMap[11607] was 'Celestron' and is changed to 'Sky-Watcher'
            orderNumToCompanyMap[order_num] = company_from_attribute

    companySanityCheck(orderNumToCompanyMap,emailToOrderNumMap,nameToOrderNumMap)

    # 3/16/2026. confirm all companies specified by order using the "Get booths from this order" property not used as standard company names.
    err = ''
    for order_num,company in orderNumToCompanyMap_for_extra_ss_rows.items():
        order_num2 = companyToOrderNumMap.get(company)
        if company in companyToOrderNumMap:
            err = f"orderNumToCompanyMap_for_extra_ss_rows has entry order_num:{order_num}, company:{company} but companyToOrderNumMap already has entry company:{company}, order_num:{order_num2}."
            error = error + '\n' + err if error else err
    if err:
        return orderNumToCompanyMap,error

    orderNumToCompanyMap.update(orderNumToCompanyMap_for_extra_ss_rows)

    return orderNumToCompanyMap,error