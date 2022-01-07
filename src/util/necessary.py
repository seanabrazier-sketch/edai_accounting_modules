def v_lookup_2(value,matching_array,return_array):

    try:
        variance_array=[(i-value)**2 for i in matching_array]
        min_val=min(variance_array)
        index=variance_array.index(min_val)
        return_value=return_array[index]
        return return_value
    except:
        return 0

def choose_with_condition(operation_condition,string_condition,array_string,array_value):
    array_selected=[]
    for i in range(len(array_string)):
        value_string=array_string[i]
        if value_string==string_condition:
            array_selected.append(array_value[i])

    if operation_condition=="min":
        return (min(array_selected))
    if operation_condition=="max":
        return(max(array_selected))
def look_up(value_lookup,array_lookup,array_value,error=True):
    if error==False:
        index=array_lookup.index(value_lookup)
        return_val=array_value[index]
        return return_val
    elif error==True:
        try:
            index = array_lookup.index(value_lookup)
            return_val = array_value[index]
            return return_val
        except:
            return "Error"
def average_array(start,end,array,step=3):
    array_return=[]
    for i in range(start,end):
        average_val=sum(array[i:i+step])/step
        array_return.append(average_val)
    return array_return










