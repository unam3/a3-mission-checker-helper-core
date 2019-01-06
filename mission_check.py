#!/usr/bin/env python2
# coding: utf-8

from __future__ import unicode_literals

import re, sys, os, json

from vehicles_list import armored 

from subprocess import call, check_output, CalledProcessError


def check(path_to_mission_folder):

    #print 'check', path_to_mission_folder

    check_results = {
        'mission_attrs': {},
        'vehicles': [],
        'slots': {},
        'errors': {},
        'warnings': {}
    }

    path_to_mission_sqm = path_to_mission_folder + '/mission.sqm'

    devnull = open(os.devnull, 'w')

    current_script_dir = os.path.dirname(os.path.abspath(__file__))


    def checkVanillaEquip(init):
        
        # proper init example:
        # call{this call compile preprocessfilelinenumbers ""equipment_infanterie\Russian_army\msv\spn_sniper.sqf"";}
        
        # unsupported init example:
        # call{[this, ""BAND"", ""LEAD""] call compile preprocessFileLineNumbers ""process_units.sqf"";}

        out = None

        init_path = path_to_mission_folder + '/' + '/'.join(
            init.split('""')[1].split('\\')
        )

        #print path_to_mission_folder
        #print relative_path
        #print init_path
        #print ''

        try:
            out = check_output(
                [
                    'grep',
                    '-i',
                    '-f', current_script_dir + '/V_Weapon.sqf',
                    init_path
                ],
                stderr=devnull
            )

        except CalledProcessError as shi:

            if (shi.returncode != 1):

                # TODO: put real errors somewhere else. into the log
                if (not check_results['errors'].get('unsupported_equipment_init')):

                    check_results['errors']['unsupported_equipment_init'] = []

                #'return code: %s for %s' % (shi.returncode, init_path)
                check_results['errors']['unsupported_equipment_init'].append(init)

        return '' if (not out) else 'vannila items: ' + out.decode('utf-8')


    def parse_vehicle_init(init):

        setVariables = init.split('this setVariable [""')

        init_options = {}
        
        # has any setVariable declaration
        if len(setVariables) > 1:

            for declaration in setVariables[1:]:

                if declaration.startswith('tf_side'):

                    # tf_side"",""east""]; 
                    #print declaration
                    #print declaration[10:].split('""')[1]

                    init_options['tf_side'] = declaration[10:].split('""')[1]

                elif declaration.startswith('WMT_Side'):

                    #print 'WMT_Side'
                    #print declaration
                    #print declaration[11:].strip(' ').split(']')[0]

                    init_options['WMT_Side'] = declaration[11:].strip(' ').split(']')[0]

        return init_options if len(init_options) else None


    wmt_disable_fuel_stations = True

    wmt_auto_med_provision = True

    wmt_side_channel_by_lr = True


    with open(path_to_mission_sqm) as opened_mission_file:
        #print opened_mission_file

        sides = {}

        vehicles = []

        class_path = []

        # units
        in_group_class = False

        group_side = False

        in_unit_class = False
        
        in_unit_custom_attrs_medic = False

        in_unit_custom_attrs_engineer = False

        in_group_custom_attr_group_id = False

        # vehicles
        in_object_class = False

        object_class_attrs = {}

        in_logic_class = False

        in_logic_class_custom_attr_disable_fuel_st = False

        in_logic_class_custom_attr_auto_med_provision = False

        in_logic_class_custom_attr_side_channel_by_lr = False

        for line in opened_mission_file:
        #for number, line in enumerate(opened_mission_file):

            #print line
            #print len(class_path), class_path

            if (re.match('\s*class ', line) and not line.endswith('{};\r\n')):

                class_name = line.split('class ')[1][:-2]

                class_path.append(class_name)

                #print 'classname is', class_name

                #print class_path

            elif (re.match('\s*};', line)):

                if (in_group_class and group_side and len(class_path) == 3):

                    in_group_class = False

                    group_side = False

                elif (in_unit_class and len(class_path) < 6):

                    in_unit_class = False

                elif (in_group_custom_attr_group_id and len(class_path) < 6):

                    in_group_custom_attr_group_id = False

                elif (in_unit_custom_attrs_medic and len(class_path) == 7):

                    in_unit_custom_attrs_medic = False

                elif (in_unit_custom_attrs_engineer and len(class_path) == 7):

                    in_unit_custom_attrs_engineer = False

                elif (in_object_class and len(class_path) == 3):

                    in_object_class = False

                    object_class_attrs = {}

                elif (in_logic_class):

                    if (len(class_path) == 3):

                        in_logic_class = False

                    # why two line prints instead of oonly one with this condition?
                    #elif (in_logic_class_custom_attr_disable_fuel_st):
                    elif (len(class_path) == 5):

                        if (in_logic_class_custom_attr_disable_fuel_st):

                            in_logic_class_custom_attr_disable_fuel_st = False
        
                        elif (in_logic_class_custom_attr_auto_med_provision):

                            in_logic_class_custom_attr_auto_med_provision = False

                        elif (in_logic_class_custom_attr_side_channel_by_lr):

                            in_logic_class_custom_attr_side_channel_by_lr = False


                # TODO: for testing purposes
                #print number, class_path
                #class_path.pop()

                if len(class_path) > 0:
                    
                    class_path.pop()

            elif (len(class_path)):

                splitted_attribute_definition = line.strip().decode('utf-8').split(' = ')

                if (len(splitted_attribute_definition) == 2):

                    attr_name, attr_value = splitted_attribute_definition

                    # in the mission file strings strings are in quotes, ends with semi
                    stripped_attr_value = attr_value[1:-2]

                    stripped_semi_attr_value = attr_value[:-1]

                    #general attr
                    if (class_path[0] == str('ScenarioData')):

                        if (attr_name == 'author'):

                            check_results['mission_attrs']['author'] = stripped_attr_value

                        if (attr_name == 'loadScreen'):

                            check_results['mission_attrs']['loadScreen'] = stripped_attr_value

                        if (attr_name == 'saving' and stripped_semi_attr_value != '0'):
                            
                            check_results['mission_attrs']['w_saving'] = True

                        if (attr_name == 'respawn' and stripped_semi_attr_value != '1'):
                            
                            check_results['mission_attrs']['w_respawn'] = True

                    elif (class_path[0] == str('CustomAttributes')):

                        #general attr
                        if ((len(class_path) == 6 and class_path[1] == 'Category0' and class_path[2] == 'Attribute0'
                            and class_path[3] == 'Value' and class_path[4] == 'data' and class_path[5] == 'value' 
                            and attr_name == 'items' and stripped_semi_attr_value != str(1))
                            or (len(class_path) == 8 and class_path[1] == 'Category0' and class_path[2] == 'Attribute0'
                            and class_path[3] == 'Value' and class_path[4] == 'data' and class_path[5] == 'value'
                            and class_path[6] == 'Item0' and class_path[7] == 'data'
                            and attr_name == 'value' and stripped_attr_value != 'Spectator')):

                                check_results['mission_attrs']['w_respawn_rulesets'] = True

                        #general attrs
                        if (len(class_path) == 3 and class_path[1] == 'Category1' and class_path[2] == 'Attribute0'
                            and attr_name == 'property' and stripped_attr_value != 'EnableTargetDebug'):

                                check_results['mission_attrs']['w_enable_target_debugging'] = True

                    elif (class_path[0] == str('Mission')):

                        if (class_name == 'Intel'):
                            #print splitted_attribute_definition
                            
                            if (attr_name == 'briefingName'):

                                check_results['mission_attrs']['briefing_name'] = stripped_attr_value

                                if (not re.match('WOG \d{2,3} (\w+\ )+\d\.\d$', stripped_attr_value, re.UNICODE)):

                                    check_results['mission_attrs']['w_briefing_name'] = True

                            # side (color, attack) - side (color, def)
                            elif (attr_name == 'overviewText'):

                                #print stripped_attr_value.encode('utf-8')
                                
                                check_results['mission_attrs']['overview_text'] = stripped_attr_value

                            elif ((attr_name == 'startWind' or attr_name == 'forecastWind')
                                and float(stripped_semi_attr_value) >= 0.41):

                                check_results['mission_attrs']['w_wind'] = int(float(stripped_semi_attr_value) * 100)

                            elif ((attr_name == 'startRain' or attr_name == 'forecastRain')
                                and float(stripped_semi_attr_value) >= 0.41):

                               check_results['mission_attrs']['w_rain'] = int(float(stripped_semi_attr_value) * 100)

                        elif (len(class_path) >= 2 and class_path[1] == str('Entities')):

                            #print in_object_class, line

                            # Mission - Entities - ItemN /w dataType = "Group"
                            # parse "side" property too
                            if (len(class_path) == 3):

                                if (attr_name == 'dataType' and stripped_attr_value == 'Group'):

                                    in_group_class = True

                                elif (attr_name == 'side' and (stripped_attr_value == 'West'
                                    or stripped_attr_value == 'East' or stripped_attr_value == 'Independent')):

                                    group_side = stripped_attr_value

                                    if (not sides.get(group_side)):
                                        sides[group_side] = []

                                    sides[group_side].append({'units': []})

                                    #print 'new group', group_side

                                elif (attr_name == 'dataType' and stripped_attr_value == 'Object'):

                                    in_object_class = True

                                elif (attr_name == 'dataType' and stripped_attr_value == 'Logic'):

                                    in_logic_class = True

                                elif (in_object_class):

                                    #print class_path

                                    #print line

                                    if (attr_name == 'type' and stripped_attr_value in armored):

                                        object_class_attrs['type'] = stripped_attr_value

                                        vehicles.append(object_class_attrs)
                                        

                                #elif (attr_name == 'id' or attr_name == 'type'):
                                #    
                                #    print attr_name, stripped_semi_attr_value

                            elif (not in_unit_class and in_group_class and group_side):

                                #print class_path

                                #print line

                                # Mission → Entities → ItemN /w dataType == 'Group' → Entities → ItemN
                                if (len(class_path) == 5 and attr_name == 'dataType' and stripped_attr_value == 'Object'):

                                    # add empty unit dict to the last group units list
                                    #print sides[group_side][-1]

                                    sides[group_side][-1]['units'].append({})

                                    #print sides[group_side][-1], '---'

                                    in_unit_class = True

                                # Mission → Entities → ItemN /w dataType == 'Group' → CustomAttributes
                                #    → AttributeN /w property == "groupID" - Value - data - 'value' property
                                elif (len(class_path) == 5 and class_path[3] == 'CustomAttributes'
                                    and attr_name == 'property' and stripped_attr_value == 'groupID'):

                                    #print 2323, in_unit_class, line

                                    in_group_custom_attr_group_id = True

                                # Mission - Entities - ItemN /w dataType = "Group" - CustomAttributes -
                                #   AttributeN /w property == "groupID" - Value - data - 'value' property
                                elif (in_group_custom_attr_group_id and len(class_path) == 7 and attr_name == 'value'):

                                    #print 'l\n', line, '\nl'

                                    sides[group_side][-1]['groupID'] = stripped_attr_value
                            
                            elif (in_unit_class):

                                # parse "side" property too. just in case

                                if (attr_name == 'init' or attr_name == 'description' or attr_name == 'type'):

                                    #print stripped_attr_value

                                    sides[group_side][-1]['units'][-1][attr_name] = stripped_attr_value
                                
                                if (attr_name == 'id'):

                                    #print stripped_semi_attr_value

                                    sides[group_side][-1]['units'][-1][attr_name] = stripped_semi_attr_value
                                
                                # isPlayable propert present only if slot is playable 
                                elif (attr_name == 'isPlayable' and stripped_semi_attr_value == '1'):

                                    sides[group_side][-1]['units'][-1][attr_name] = True

                                # Mission - Entities - ItemN /w dataType = "Group" - Entities - ItemN - CustomAttributes
                                elif (len(class_path) == 7 and class_path[5] == 'CustomAttributes'
                                    and attr_name == 'property'):

                                    if (stripped_attr_value == 'ace_isMedic'):

                                        in_unit_custom_attrs_medic = True

                                    elif (stripped_attr_value == 'ace_isEngineer'):

                                        in_unit_custom_attrs_engineer = True

                                elif (in_unit_custom_attrs_medic and len(class_path) == 9 and class_path[7] == 'Value'
                                    and class_path[8] == 'data'):

                                    #print class_path, len(class_path)

                                    #print 'ace_isMedic', stripped_semi_attr_value
                                    
                                    sides[group_side][-1]['units'][-1]['ace_isMedic'] = stripped_semi_attr_value

                                elif (in_unit_custom_attrs_engineer and len(class_path) == 9 and class_path[7] == 'Value'
                                    and class_path[8] == 'data'):

                                    #print 'ace_isEngineer', stripped_semi_attr_value

                                    sides[group_side][-1]['units'][-1]['ace_isEngineer'] = stripped_semi_attr_value

                                #print class_path
                                #print line

                            elif (in_object_class):

                                #print class_path

                                #print line

                                if (len(class_path) == 4 and class_path[3] == 'Attributes'):
                                    
                                    if (attr_name == 'lock' or attr_name == 'init' or attr_name == 'fuel'):

                                        object_class_attrs[attr_name] = stripped_attr_value

                            elif (in_logic_class):

                                #print class_path

                                #print line

                                # CustomAttributes - AttributeN
                                if (len(class_path) == 5 and class_path[3] == 'CustomAttributes' and
                                    attr_name == 'property'):
                                    
                                    if (stripped_attr_value == 'WMT_Main_DisableFuelSt'):
                                    
                                        in_logic_class_custom_attr_disable_fuel_st = True

                                    elif (stripped_attr_value == 'WMT_Main_AutoMedicine'):
                                    
                                        in_logic_class_custom_attr_auto_med_provision = True

                                    elif (stripped_attr_value == 'WMT_Main_SideChannelByLR'):
                                    
                                        in_logic_class_custom_attr_side_channel_by_lr = True

                                elif (in_logic_class_custom_attr_disable_fuel_st and attr_name == 'value' and
                                    stripped_semi_attr_value == '0'):
                                    
                                    wmt_disable_fuel_stations = False

                                elif (in_logic_class_custom_attr_auto_med_provision and attr_name == 'value' and
                                    stripped_semi_attr_value == '0'):
                                    
                                    wmt_auto_med_provision = False

                                elif (in_logic_class_custom_attr_side_channel_by_lr and attr_name == 'value' and
                                    stripped_semi_attr_value == '0'):
                                    
                                    wmt_side_channel_by_lr = False


        check_results['mission_attrs']['wmt_disable_fuel_stations'] = wmt_disable_fuel_stations

        check_results['mission_attrs']['wmt_auto_med_provision'] = wmt_auto_med_provision

        check_results['mission_attrs']['wmt_side_channel_by_lr'] = wmt_side_channel_by_lr


        # 0 if found, 1 if not and 2 if error
        wog3_no_auto_long_range_radio = True if not call(
            [
                'grep',
                #'-i',
                '-o',
                # stop after first match
                #'-m', '1',
                'wog3_no_auto_long_range_radio = true;',
                path_to_mission_folder + '/init.sqf'
            ],
            stdout=devnull,
            stderr=devnull
        ) else False


        groupLeadersUniqueInits = set()

        if (wog3_no_auto_long_range_radio):
            
            check_results['mission_attrs']['wog3_no_auto_long_range_radio'] = True

        else:
            
            # Check equpment of first units in squads (team leaders) for backpacks
            # If unit has backpack, then radio will be spawned behind him
            for side in sides:
                
                for group in sides[side]:

                    #print side, group.get('groupID') or 'group without groupID', group['units'][0]

                    init = group['units'][0].get('init')

                    if (init):
                        
                        groupLeadersUniqueInits.add(init)

                    #else:
                    #    
                    #    print '^^^ has no init'

            for init in groupLeadersUniqueInits:
                
                #print init

                # 0 if found, 1 if not and 2 if error
                if not call(
                    [
                        'grep',
                        '-i',
                        '-o',
                        # stop after first match
                        '-m', '1',
                        #'^_this addBackpack',
                        'addBackpack',
                        path_to_mission_folder + '/' + '/'.join(
                            init.split('""')[1].split('\\')
                        )
                    ],
                    stdout=devnull,
                    stderr=devnull
                ):
                    if not check_results['warnings']['backpacks_dup']:

                        check_results['warnings']['backpacks_dup'] = []
                        
                    check_results['warnings']['backpacks_dup'].append(init)


        playable_slots = {}

        uniqueUnitInits = set()

        # get slots count
        for side, groups in sides.items():
            
            if (not playable_slots.get(side)):

                playable_slots[side] = 0

            for group in groups:

                for unit in group['units']:

                    uniqueUnitInits.add(unit.get('init'))

                    if (unit.get('isPlayable')):

                        playable_slots[side] += 1

        check_results['slots']['playable_slots'] = playable_slots


        #clientside this!
        #if (total_playable_slots > 190):
        #    
        #    check_results['slots']['too_much_slots'] = True


        sorted_inits = sorted(uniqueUnitInits)

        #print sorted_inits

        unique_sorted_inits = []
        
        for init in sorted_inits:
            
            unique_init = {'init': init}

            # None if no init
            if (init):
                
                #print 'init:', init

                splitted_init = init.split('""')

                if (len(splitted_init) > 1):

                    unique_init['splitted_init'] = splitted_init[1]

                    # 0 if found, 1 if not and 2 if error
                    unique_init['has_no_radio'] = bool(call(
                        [
                            'grep',
                            '-i',
                            '-o',
                            # stop after first match
                            #'-m', '1',
                            'itemradio',
                            path_to_mission_folder + '/' + '/'.join(
                                splitted_init[1].split('\\')
                            )
                        ],
                        stdout=devnull,
                        stderr=devnull
                    ))

                    vanilla_equipment = checkVanillaEquip(init)

                    if len(vanilla_equipment):

                        unique_init['vanilla_equipment'] = vanilla_equipment

            unique_sorted_inits.append(unique_init)

        devnull.close()

        check_results['slots']['unique_inits'] = unique_sorted_inits


        #clientside this!
        #for side, groups in sides.items():
        #    
        #    print '\n', side, 'has', playable_slots[side], 'playable slots'

        #    for group in groups:

        #        print '\nGROUP ID:', group.get('groupID') or 'group without groupID'

        #        for unit in group['units']:

        #            if (unit.get('isPlayable')):

        #                print '\n', unit['description'], unit['type'],  unit.get('ace_isEngineer'),\ unit.get('ace_isMedic')

        #                print unit.get('init')

        #            else:
        #                
        #                print 'next unit is not playable!', unit

        
        check_results['sides'] = sides

        check_results['vehicles'] = vehicles

        return check_results


if __name__ == "__main__":
    
    # this and singlequotes in templates around output wasn't good enough
    #print json.dumps(check_results, ensure_ascii=False)
    print json.dumps(json.dumps(check(sys.argv[1]), ensure_ascii=False), ensure_ascii=False)
