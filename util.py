import pisqpipe as pp
import random
import re
import copy
import datetime as dt

turn_dict = {False: 2, True: 1}
case_order = {'L5': 0, 'L4': 1, 'L3': 2, 'S4': 3, 'L2': 4, 'S3': 5, 'S2': 6, 'L1': 7, 'S1': 8, 'None': 9}
score_list = {'L5': 100000, 'L4': 50000, 'L3': 500, 'S4': 300, 'L2': 100, 'S3': 50, 'S2': 5, 'L1': 2, 'S1': 1,
              'None': 0}


def score_ratio(num):
    if num == 0:
        return 0.5
    else:
        prop = num / abs(num)
        mag = min(abs(num), 10000)
        return prop * mag / 20000 + 1 / 2


class StateNode:
    def __init__(self, board, turn, parent=None, reach_move=None, num_sim=0, num_win=0):
        self.board = board
        self.turn = turn
        self.num_sim = num_sim
        self.num_win = num_win
        self.parent = parent
        self.children = []
        self.modified = []
        self.reach_move = reach_move
        self.available, self.plugged = self.get_info()
        self.hint = self.suggest_position()
        self.feature = self.feature_save()
        self.win = self.terminate()
        self.evaluation = self.scoring()

    def get_info(self):
        available, plugged = [], []
        for x in range(pp.width):
            for y in range(pp.height):
                if not self.board[x][y]:
                    available.append((x, y))
                else:
                    plugged.append((x, y))
        return available, plugged

    def __get_line(self, row, col, direction):
        # from x,y,extract a line(list) which passes point(x,y) with direction "dir"
        # dir: An int from 1 to 4, indicates horizontal, vertical, and two diagonal case.
        bd = self.board
        if direction == 1:
            return bd[row]
        elif direction == 2:
            ret = []
            for ln in bd:
                ret.append(ln[col])
            return ret
        elif direction == 3:
            line = []
            a, b = len(bd), len(bd[0])
            for i in range(a):
                for j in range(b):
                    if i + j == row + col:
                        line.append(bd[i][j])
            return line
        elif direction == 4:
            line = []
            a, b = len(bd), len(bd[0])
            for i in range(a):
                for j in range(b):
                    if j - i == col - row:
                        line.append(bd[i][j])
            return line

    def __feature_detect(self, line, turn):
        # detect feature from given line, return most valuable case.
        # line = list(line)
        answer = []
        # 如果turn是2的话 就把1、2互换，反之不变。
        if turn == 2:
            for i in range(len(line)):
                if line[i] == 1:
                    line[i] = 2
                elif line[i] == 2:
                    line[i] = 1
        # 把list转换为字符串用正则表达式查找pattern
        line = list(map(str, line))
        line = ''.join(line)

        if re.findall('11', line):
            if re.findall('111', line):
                if re.findall('1111', line):
                    if re.findall('11111', line):
                        return 'L5'
                    elif re.findall('011110', line):
                        return 'L4'
                    elif re.findall('[32]11110', line) or re.findall('01111[32]', line):
                        answer.append('S4')
                elif re.findall('11101', line) or re.findall('10111', line):
                    answer.append('S4')
                elif re.findall('01110', line):
                    answer.append('L3')
                elif re.findall('[32]11100', line) or re.findall('00111[32]', line):
                    answer.append('S3')
                elif re.findall('[32]01110[32]', line):
                    answer.append('S3')
            elif re.findall('11011', line):
                answer.append('S4')
            elif re.findall('010110', line) or re.findall('011010', line):
                answer.append('L3')
            elif re.findall('01011[23]', line) or re.findall('[23]11010', line):
                answer.append('S3')
            elif re.findall('01101[23]', line) or re.findall('[23]10110', line):
                answer.append('S3')
            elif re.findall('0100110', line) or re.findall('0110010', line):
                answer.append('S3')
            elif re.findall('0110', line):
                answer.append('L2')
            elif re.findall('[23]1100', line) or re.findall('0011[23]', line):
                answer.append('S2')
        elif re.findall('01010', line):
            answer.append('L2')
        elif re.findall('010010', line):
            answer.append('L2')
        elif re.findall('00101[23]', line) or re.findall('[23]10100', line):
            answer.append('S2')
        elif re.findall('01001[23]', line) or re.findall('[23]10010', line):
            answer.append('S2')
        elif re.findall('010', line):
            answer.append('L1')
        elif re.findall('[23]10', line) or re.findall('01[23]', line):
            answer.append('S1')

        if not answer:
            return 'None'
        # return the most valuable case in answer list
        for ii, a in enumerate(answer):
            answer[ii] = (a, case_order[a])
        return sorted(answer, key=lambda kv: kv[1])[0][0]

    def __feature_extract(self, turn=1):
        case_count = {}
        direction = 1
        size = len(self.board)
        for i in range(size):
            line = self.__get_line(i, 0, direction)
            line = [3] + line + [3]
            # 3 indicates there is a wall
            case = self.__feature_detect(line, turn)
            case_count[case] = case_count.get(case, 0) + 1

        direction = 2
        for i in range(size):
            line = self.__get_line(0, i, direction)
            line = [3] + line + [3]
            # 3 indicates there is a wall
            case = self.__feature_detect(line, turn)
            case_count[case] = case_count.get(case, 0) + 1

        direction = 4
        for row in range(size - 1, -1, -1):
            line = self.__get_line(row, 0, direction)
            line = [3] + line + [3]
            # 3 indicates there is a wall
            case = self.__feature_detect(line, turn)
            case_count[case] = case_count.get(case, 0) + 1
        for column in range(1, size):
            line = self.__get_line(0, column, direction)
            line = [3] + line + [3]
            # 3 indicates there is a wall
            case = self.__feature_detect(line, turn)
            case_count[case] = case_count.get(case, 0) + 1

        direction = 3
        for column in range(size):
            line = self.__get_line(0, column, direction)
            line = [3] + line + [3]
            # 3 indicates there is a wall
            case = self.__feature_detect(line, turn)
            case_count[case] = case_count.get(case, 0) + 1
        for row in range(1, size):
            line = self.__get_line(row, size - 1, direction)
            line = [3] + line + [3]
            # 3 indicates there is a wall
            case = self.__feature_detect(line, turn)
            case_count[case] = case_count.get(case, 0) + 1
        return case_count

    def __get_diff_feature(self, turn=1):
        ((x, y), color) = self.reach_move
        old_feature = copy.deepcopy(self.parent.feature[turn - 1])

        for direction in [1, 2, 3, 4]:
            line = self.parent.__get_line(x, y, direction)
            line = [3] + line + [3]
            # 3 indicates wall.
            case = self.__feature_detect(line, turn)
            old_feature[case] = old_feature.get(case, 0) - 1
        for direction in [1, 2, 3, 4]:
            line = self.__get_line(x, y, direction)
            line = [3] + line + [3]
            case = self.__feature_detect(line, turn)
            old_feature[case] = old_feature.get(case, 0) + 1

        key_list = list(old_feature.keys())
        for key in key_list:
            if old_feature[key] == 0:
                del old_feature[key]
        return old_feature

    def feature_save(self):
        if self.parent is not None:
            return [self.__get_diff_feature(turn=1), self.__get_diff_feature(turn=2)]
        else:
            return [self.__feature_extract(1), self.__feature_extract(2)]

    # judge the terminate state and the winner, 0 for non-terminal, 1 for win, 2 for lose, 3 for tied
    def terminate(self):
        if self.feature[0].get('L5', 0) > 0:
            return 1
        elif self.feature[1].get('L5', 0) > 0:
            return 2
        elif len(self.available) == 0:
            return 3
        return 0

    def scoring(self):
        score = 0; me = int(self.turn); rival = int(not self.turn)
        if self.feature[me].get('L5', 0) > 0:
            return 100000
        elif self.feature[rival].get('L4', 0) > 0:
            return -100000
        elif self.feature[rival].get('S4', 0) > 0:
            return -40000
        elif self.feature[me].get('L4', 0) > 0:
            return 40000
        elif (self.feature[me].get('S4', 0) > 1) or \
                (self.feature[me].get('S4', 0) > 0 and self.feature[me].get('L3', 0) > 0):
            return 20000
        elif self.feature[rival].get('L3', 0) > 1:
            return -20000
        elif self.feature[rival].get('L3', 0) > 0:
            return -10000
        elif self.feature[me].get('L3', 0) > 1:
            return 10000
        else:
            for key in self.feature[me].keys():
                score += score_list[key] * self.feature[me][key]
            for key in self.feature[rival].keys():
                score += -score_list[key] * self.feature[rival][key]
            return score

    # select the position of the better choice: 3 nearby position of current board
    # return the list of these position
    def suggest_position(self):
        def draw_square(loca):
            temp = []; size = 2
            for i in range(size):
                for j in range(size):
                    temp.append((loca[0] + i, loca[1] + j)); temp.append((loca[0] + i, loca[1] - j))
                    temp.append((loca[0] - i, loca[1] + j)); temp.append((loca[0] - i, loca[1] - j))
            square = set(temp)
            return square

        avail = set(self.available)
        if (self.parent is None) or (not self.parent.hint):
            res = []
            for each in self.plugged:
                judge_area = draw_square(each)
                ele = list(judge_area & avail)
                if ele:
                    res.extend(ele)
            return list(set(res))
        else:
            inherit = copy.deepcopy(self.parent.hint)
            inherit.remove(self.reach_move[0])
            inherit = set(inherit)
            new_square = draw_square(self.reach_move[0])
            res = list((new_square & avail) | inherit)
            return res

    def get_child(self):

        def group_get_child(gp):
            for i in range(len(gp)):
                if gp[i]:
                    gp[i].sort(key=lambda x: x[1], reverse=True)
                    return [gp[i][0][0]]
            return []

        if len(self.plugged) == 0:
            new_board = copy.deepcopy(self.board)
            posi = (pp.width//2, pp.height//2)
            new_board[posi[0]][posi[1]] = turn_dict[self.turn]
            temp = StateNode(new_board, not self.turn, parent=self, reach_move=(posi, turn_dict[self.turn]))
            self.children = [temp]
        else:
            res = []; deny = False; group = [[],[],[],[],[]]
            for each in self.hint:
                new_board = copy.deepcopy(self.board)
                new_board[each[0]][each[1]] = turn_dict[not self.turn]
                atemp = StateNode(new_board, self.turn, parent=self, reach_move=(each, turn_dict[not self.turn]))
                new_board[each[0]][each[1]] = turn_dict[self.turn]
                temp = StateNode(new_board, not self.turn, parent=self, reach_move=(each, turn_dict[self.turn]))
                if temp.evaluation == 100000:
                    deny = True; self.children = [temp]
                    break
                elif atemp.evaluation == 100000:
                    group[0].append((temp, atemp.evaluation))
                elif temp.evaluation >= 20000:
                    group[1].append((temp, temp.evaluation))
                elif atemp.evaluation >= 20000:
                    group[2].append((temp, atemp.evaluation))
                elif temp.evaluation == 10000:
                    group[3].append((temp, temp.evaluation))
                elif atemp.evaluation == 10000:
                    group[4].append((temp, atemp.evaluation))
                else:
                    res.append(temp)
            if not deny:
                self.children = group_get_child(group)
                if not self.children:
                    length = min(len(res), 3)
                    res.sort(key=lambda x: x.evaluation, reverse=True)
                    self.children = res[:length]

    def modified_score(self):
        additive = 0; res = []
        for child in self.children:
            eva = child.evaluation
            res.append(eva)
            if eva < 0:
                additive -= eva
        for i in range(len(res)):
            res[i] += additive
        self.modified = res

    # resample based on score(used only in random_play)
    def score_sample(self):
        self.modified_score()
        total = sum(self.modified); rand_num = random.randint(0, total)
        if not total == 0:
            for i in range(len(self.modified)):
                rand_num -= self.modified[i]
                if rand_num <= 0:
                    return self.children[i]
        else:
            return random.sample(self.children, 1)[0]

    def random_play(self):
        self.get_child()
        res = self.score_sample()
        return res

    def update_parent(self, sim_plus, win_plus):
        current_node = self
        while current_node is not None:
            current_node.num_sim += sim_plus
            current_node.num_win += win_plus
            current_node = current_node.parent

    def simulate_leaf(self, maxiter, begin_time, maxtime):
        num_child = len(self.children)
        if num_child:
            i = 0; sim_plus = 0; win_plus = 0
            while (i < num_child) and ((dt.datetime.now() - begin_time).seconds < maxtime):
                child = self.children[i]; sim = 0; win = 0
                for _ in range(maxiter):
                    backup_child = copy.deepcopy(child)
                    step_count = 0
                    while (not backup_child.win) and (step_count < 2):
                        backup_child = backup_child.random_play()
                        step_count += 1
                    if backup_child.win == 0:
                        win += score_ratio(backup_child.evaluation)
                    elif backup_child.win == 1:
                        win += 1
                    elif backup_child.win == 3:
                        win += 0.5
                    sim += 1
                self.children[i].num_sim = sim; self.children[i].num_win = win
                sim_plus += sim; win_plus += win
                i += 1
            self.update_parent(sim_plus=sim_plus, win_plus=win_plus)

    def pick_up(self):
        self.modified_score()
        total_modified = sum(self.modified)
        num_child = len(self.modified)
        if num_child > 0:
            if num_child == 1:
                return self.children[0]
            else:
                pick = self.children[0]
                if total_modified:
                    if pick.num_sim:
                        best_score = self.modified[0] / total_modified + pick.num_win / pick.num_sim
                    else:
                        best_score = self.modified[0] / total_modified
                    for i in range(1, num_child):
                        this_child = self.children[i]
                        if this_child.num_sim:
                            new_score = self.modified[i] / total_modified + this_child.num_win / this_child.num_sim
                        else:
                            new_score = self.modified[i] / total_modified
                        if new_score > best_score:
                            best_score = new_score; pick = this_child
                else:
                    if pick.num_sim:
                        best_score = pick.num_win / pick.num_sim
                    else:
                        best_score = 0.5
                    for i in range(1, num_child):
                        this_child = self.children[i]
                        if this_child.num_sim:
                            new_score = this_child.num_win / this_child.num_sim
                        else:
                            new_score = 0.5
                        if new_score > best_score:
                            best_score = new_score; pick = this_child
                return pick
        else:
            return None


class MCTS:
    def __init__(self, board, maxiter=1, maxtime=2):
        self.state = StateNode(board, True)
        self.maxtime = maxtime
        self.maxiter = maxiter

    def solve(self):
        begin_time = dt.datetime.now(); init_state = copy.deepcopy(self.state)
        same_count = 0
        while (dt.datetime.now() - begin_time).seconds < self.maxtime:
            next_state = init_state.pick_up()
            if next_state is None:
                init_state.get_child()
                if len(init_state.children) == 1:
                    pick = init_state.children[0]
                    break
                else:
                    init_state.simulate_leaf(self.maxiter, begin_time, self.maxtime)
                    pick = init_state.pick_up()
                    continue
            else:
                compare = copy.deepcopy(next_state)
                while next_state.children:
                    next_state = next_state.pick_up()
                next_state.get_child()
                next_state.simulate_leaf(self.maxiter, begin_time, self.maxtime)
                pick = init_state.pick_up()
                if compare.reach_move == pick.reach_move:
                    same_count += 1
                    if same_count > 1:
                        break
        return pick

    def get_action(self):
        ans = self.solve()
        return ans.reach_move[0]


# pyinstaller.exe util.py example.py pisqpipe.py --name pbrain-pyrandom.exe --onefile