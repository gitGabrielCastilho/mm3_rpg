from django.core.management.base import BaseCommand
from personagens.models import Vantagem


VANTAGENS = [
    ("Ação em Movimento", "Mova-se tanto antes quanto depois de sua ação padrão."),
    ("Agarrar Aprimorado", "Faça ataques de agarrar com apenas uma mão."),
    ("Agarrar Preciso", "Substitui Des por For em ataques para agarrar."),
    ("Agarrar Rápido", "Quando acerta um ataque desarmado, pode fazer um teste de agarrar como ação livre."),
    ("Ambiente Favorito", "Bônus de circunstância no ataque ou na defesa em determinado ambiente."),
    ("Arma Improvisada", "Use a perícia Combate Desarmado com armas improvisadas, com bônus de dano de +1."),
    ("Armação", "Transfira o benefício de uma perícia de interação para um aliado."),
    ("Ataque à Distância", "Bônus de +1 em testes de ataque à distância por graduação."),
    ("Ataque Acurado", "Troque a CD do efeito por um bônus de ataque."),
    ("Ataque Corpo-a-Corpo", "Bônus de +1 em testes de ataque corpo-a-corpo por graduação."),
    ("Ataque Defensivo", "Troque um bônus de ataque por um bônus de defesa ativa."),
    ("Ataque Dominó", "Ganhe um ataque extra quando incapacitar um capanga."),
    ("Ataque Imprudente", "Troque defesa ativa por um bônus de ataque."),
    ("Ataque Poderoso", "Troque bônus de ataque por bônus de efeito."),
    ("Ataque Preciso", "Ignore penalidades em testes de ataque devido a cobertura ou camuflagem."),
    ("Crítico Aprimorado", "+1 na ameaça de crítico com um ataque específico por graduação."),
    ("Defesa Aprimorada", "Bônus de +2 em uma defesa ativa quando você usa a ação defender-se."),
    ("Derrubar Aprimorado", "Sem penalidade para usar a ação derrubar."),
    ("Desarmar Aprimorado", "Sem penalidade para usar a ação desarmar."),
    ("Esquiva Fabulosa", "Você não fica vulnerável quando surpreso ou desatento."),
    ("Estrangular", "Sufoca um oponente que você tenha agarrado."),
    ("Evasão", "Bônus de circunstância para evitar ataques de área."),
    ("Imobilizar Aprimorado", "Penalidade de circunstância de –5 para escapar de você."),
    ("Iniciativa Aprimorada", "Bônus de +4 por graduação em testes de iniciativa."),
    ("Luta no Chão", "Sem penalidade por lutar caído."),
    ("Maestria em Arremesso", "Bônus de dano de +1 com armas arremessadas por graduação."),
    ("Mira Aprimorada", "Dobra os bônus de circunstância por mirar."),
    ("Prender Arma", "Tentativa livre de desarme quando você se defende."),
    ("Quebrar Aprimorado", "Sem penalidade para usar a ação quebrar."),
    ("Quebrar Arma", "Tentativa livre de quebrar quando você se defende."),
    ("Redirecionar", "Use Enganação para redirecionar um ataque que falhe para outro alvo."),
    ("Rolamento Defensivo", "Bônus de defesa ativa de +1 em Resistência por graduação."),
    ("Saque Rápido", "Saque uma arma como uma ação livre."),
    ("Artífice", "Use Especialidade: Magia para criar dispositivos mágicos temporários."),
    ("Assustar", "Use Intimidação para fintar em combate."),
    ("Atraente", "Bônus de circunstância em perícias de interação baseado em sua aparência."),
    ("Bem Informado", "Teste imediato de Investigação ou Percepção para saber alguma coisa."),
    ("Bem Relacionado", "Chame ajuda ou consiga favores com um teste de Persuasão."),
    ("Contatos", "Faça um teste inicial de Investigação em um minuto."),
    ("Empatia com Animais", "Use perícias de interação com animais."),
    ("Esconder-se à Plena Vista", "Esconda-se quando observado sem precisar de uma distração."),
    ("Fascinar", "Use uma perícia de interação para prender a atenção dos outros."),
    ("Faz Tudo", "Use qualquer perícia sem treinamento."),
    ("Ferramentas Aprimoradas", "Sem penalidade por usar perícias sem as ferramentas apropriadas."),
    ("Finta Ágil", "Finte usando a perícia Acrobacia ou sua velocidade."),
    ("Idiomas", "Fale e compreenda idiomas adicionais."),
    ("Inimigo Favorito", "Bônus de circunstância em testes contra um tipo de oponente."),
    ("Inventor", "Use Tecnologia para criar dispositivos temporários."),
    ("Maestria em Perícia", "Realize testes de rotina com uma perícia sob quaisquer circunstâncias."),
    ("Rastrear", "Use Percepção para seguir rastros."),
    ("Ritualista", "Use Especialidade: Magia para criar e realizar rituais."),
    ("Tontear", "Use Enganação ou Intimidação para deixar um oponente tonto."),
    ("Zombar", "Use Enganação para desmoralizar em combate."),
    ("Esforço Supremo", "Gaste um ponto heróico para ganhar um 20 efetivo em um teste específico."),
    ("Inspirar", "Gaste um ponto heróico para conceder a seus aliados um bônus de circunstância de +1 por graduação."),
    ("Liderança", "Gaste um ponto heróico para remover uma condição de um aliado."),
    ("Sorte de Principiante", "Gaste um ponto heróico para ganhar 5 graduações temporárias em uma perícia."),
    ("Sorte", "Rerole uma rolagem uma vez por graduação."),
    ("Tomar a Iniciativa", "Gaste um ponto heróico para agir primeiro na ordem de iniciativa."),
    ("Avaliação", "Use Intuição para descobrir as habilidades de combate do oponente."),
    ("Benefício", "Ganhe uma gratificação ou benefício adicional."),
    ("Capanga", "Ganhe um seguidor ou capanga com (15 x graduação) pontos de poder."),
    ("De Pé", "Passe de caído para em pé como uma ação livre."),
    ("Destemido", "Imune a efeitos de medo."),
    ("Duro de Matar", "Estabilize automaticamente quando moribundo."),
    ("Equipamento", "5 pontos de equipamento por graduação."),
    ("Esforço Extraordinário", "Ganhe dois benefícios quando usando esforço extra."),
    ("Interpor-se", "Sofra um ataque mirado contra um aliado."),
    ("Memória Eidética", "Você se lembra de tudo, bônus de circunstância de +5 para se lembrar das coisas."),
    ("Parceiro", "Ganhe um parceiro com (5 x graduação) pontos de poder."),
    ("Segunda Chance", "Rerole um teste falho contra uma ameaça uma vez."),
    ("Tolerância Maior", "+5 em testes envolvendo tolerância."),
    ("Trabalho em Equipe", "+5 de bônus para ajudar em testes de equipe."),
    ("Transe", "Entre em um transe parecido com a morte que diminui as funções vitais."),
]


class Command(BaseCommand):
    help = "Carrega/atualiza a tabela de Vantagens com a lista padrão. Idempotente."

    def handle(self, *args, **options):
        created, updated = 0, 0
        for nome, descricao in VANTAGENS:
            obj, was_created = Vantagem.objects.update_or_create(
                nome=nome,
                defaults={"descricao": descricao},
            )
            if was_created:
                created += 1
            else:
                updated += 1
        self.stdout.write(self.style.SUCCESS(
            f"Vantagens processadas com sucesso. Criadas: {created}, Atualizadas: {updated}."
        ))
